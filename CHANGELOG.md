CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録しています。
このプロジェクトはセマンティックバージョニングに従います。

フォーマットの説明:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能

Unreleased
----------

（現状なし）

0.1.0 - 2026-03-27
-----------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py にてバージョン 0.1.0 と主要サブパッケージを公開（data, strategy, execution, monitoring）。
  - 設定 / 環境変数管理（src/kabusys/config.py）
    - .env/.env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して行い、CWD に依存しない実装。
    - .env 行パーサーは以下をサポート:
      - コメント行（#）・空行の無視
      - export KEY=val 形式のサポート
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - インラインコメントの適切な無視（クォート外、直前がスペース/タブの場合）
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - Settings クラスにより主要設定値をプロパティで公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
    - 環境変数未設定時に ValueError を投げる _require ユーティリティを提供。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
  - AI (自然言語処理) モジュール（src/kabusys/ai 以下）
    - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を集約し、銘柄単位で OpenAI (gpt-4o-mini) に JSON モードで問い合わせてセンチメント（-1.0〜1.0）を算出。
      - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
      - バッチサイズ、1銘柄あたりの記事上限文字数/件数、レスポンスバリデーション、スコアクリップ、部分成功時のテーブル書き換えロジック（DELETE → INSERT）を実装。
      - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを採用。致命的でない場合はフェイルセーフでスキップして処理継続。
      - OpenAI API キーが未設定の場合は ValueError を発生させる明示的チェック。
      - テスト容易化のため _call_openai_api を差し替え可能に実装。
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
      - prices_daily と raw_news を参照し、計算結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
      - LLM 呼び出しは独立実装、API 失敗時は macro_sentiment=0.0 としてフェイルセーフ処理。
      - リトライ・バックオフ・エラーハンドリングを実装。
      - ルックアヘッドバイアス回避の設計（datetime.today() 等を直接参照しない、SQL で date < target_date を使用）。
  - データプラットフォーム・ユーティリティ（src/kabusys/data 以下）
    - カレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar テーブルの読み書き・営業日判定ロジックを提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ実装。
      - DB 登録データ優先、未登録日には曜日ベースでのフォールバック（週末除外）。探索範囲上限を設け無限ループ防止。
      - calendar_update_job により J-Quants API から差分取得し、バックフィル・健全性チェックを行う夜間バッチ処理を実装。
    - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
      - 差分取得 → 保存（jquants_client の save_* を利用） → 品質チェック（quality モジュール）までを想定した ETLResult データクラスを提供。
      - ETLResult は実行メトリクス（取得件数・保存件数・品質問題・エラー）を保持し、辞書化可能。
      - デフォルトで最小データ日やバックフィル等の定義を持つ。
  - 研究（research）モジュール（src/kabusys/research 以下）
    - factor_research.py
      - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Value（PER/ROE）、Liquidity 指標の計算関数（calc_momentum, calc_volatility, calc_value）を実装。
      - DuckDB を用いた SQL ベースの計算で、欠損やデータ不足時の None 処理を考慮。
    - feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリ（factor_summary）を実装。
      - pandas など外部依存なしで実装。ランク計算は同順位に平均ランクを与える仕様。
    - research パッケージ __init__ で主要関数を再エクスポート。
  - テスト・デバッグ配慮
    - OpenAI 呼び出し部分はテストで差し替え可能（関数を局所実装しているためモジュール間でプライベート関数を共有しない設計）。
    - DuckDB executemany に関する互換性考慮（空リストチェック等）。

Notes / 操作上の注意
- 環境変数:
  - 必須: OPENAI_API_KEY（AI 呼び出しを行う場合）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI:
  - gpt-4o-mini を想定（JSON mode を利用）。SDK の OpenAI クラスに依存。SDK の将来の変更に合わせてハンドリング済み（status_code の有無等に配慮）。
  - API 呼び出し失敗時はフェイルセーフ動作を優先（スコアを 0.0 にフォールバック、例外は基本的に上位に伝播させない設計。ただし DB 書込失敗時は例外を伝播）。
- ルックアヘッドバイアス対策:
  - ニュース / レジーム判定 / ファクター計算等、すべてターゲット日を明示的に受け取り、datetime.today() を直接参照しない実装にしている。
- DB 書き込みは冪等性を意識:
  - ai_scores / market_regime / market_calendar などへの書き込みは既存行の削除→挿入、または ON CONFLICT 相当で冪等に更新する設計を採用。

Changed
- （今回の初回リリースにおける変更履歴は無し）

Fixed
- （今回の初回リリースにおける修正履歴は無し）

Removed
- （今回の初回リリースにおける削除履歴は無し）

参考
- 実装は DuckDB を主要なローカル分析 DB として想定しています。
- jquants_client, quality など外部依存モジュールへのインターフェースはコード内で使用します（実デプロイ時にはそれらの実装またはモックが必要です）。