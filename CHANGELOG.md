Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測して記載しています。日付は本日（2026-03-29）を想定しています。必要に応じて日付や詳細を調整してください。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
安定版リリースごとにセクションを追加してください。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初回リリース (kabusys 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数の自動読み込み機能を実装
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - プロジェクトルートは .git または pyproject.toml を手掛かりに探索（CWD非依存）
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能
    - .env 行パーサーで以下に対応:
      - コメント行（#）の扱い、export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理
    - .env 読み込み時の保護機構:
      - OSの既存環境変数は protected として上書きを防止
      - override フラグで .env.local による上書きを許可
    - Settings クラスを提供しアプリ設定を型安全に取得
      - J-Quants / kabuステーション / Slack / DBパス等のプロパティ（例: jquants_refresh_token, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）
      - KABUSYS_ENV と LOG_LEVEL の検証（allowed 値チェック）
      - is_live / is_paper / is_dev のユーティリティ

- AI ニュース処理（LLM を用いたスコアリング）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価し ai_scores テーブルへ保存する処理を実装
    - 機能の概要:
      - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）
      - 銘柄ごとに最新 N 記事・文字数でトリムしてプロンプト作成
      - バッチ送信（1 API 呼び出しで最大 _BATCH_SIZE=20 銘柄）
      - レスポンス検証（JSON 抽出、results フィールド、code/score の検証）
      - スコアを ±1.0 にクリップ
      - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に他コードは保護）
    - レジリエンス:
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ（_MAX_RETRIES）
      - それ以外のエラーは個別チャンクをスキップして継続（フェイルセーフ）
    - テスト容易性:
      - _call_openai_api を patch してテスト可能

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定モジュールを実装
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と
        マクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定
      - 処理フロー:
        - ma200_ratio 算出（ルックアヘッドバイアスを避けるため target_date 未満のデータのみ使用）
        - マクロキーワードで raw_news をフィルタして記事タイトルを取得
        - OpenAI（gpt-4o-mini）で JSON 出力により macro_sentiment を取得
        - 重み付け合成とクリッピング、閾値判定
        - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - レジリエンス:
      - API 失敗・パース失敗時は macro_sentiment=0.0 として継続（警告ログ）
      - OpenAI 呼び出しのリトライ/バックオフを実装
    - 実装上の配慮:
      - news_nlp の内部実装と結合しない（別の _call_openai_api 実装）
      - ルックアヘッドバイアス防止を明示的に設計

- 研究用（Research）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）を実装
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離
      - Value: PER, ROE（raw_financials から最近のレポートを取得）
      - Volatility: 20日 ATR、相対 ATR（atr_pct）
      - Liquidity: 20日平均売買代金、出来高比率
    - 全て DuckDB (prices_daily / raw_financials) のみ参照、外部 API にはアクセスしない
    - データ不足時は None を返す（堅牢性）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ランク変換 (rank)、統計サマリー (factor_summary) を提供
    - 実装は標準ライブラリ（pandas 等非依存）、小規模データ解析に適した形で提供
    - スピアマンのランク相関（IC）は ties の平均ランク処理を含む
  - src/kabusys/research/__init__.py で主要関数を再公開

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーの管理機能を提供
      - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day, prev_trading_day）、期間内の営業日列挙 (get_trading_days)、SQ 日判定 (is_sq_day)
      - market_calendar テーブルがない場合の曜日ベースのフォールバック実装
      - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェックあり）
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプライン関連:
      - ETLResult データクラスを定義（取得数・保存数・品質チェック・エラー情報等を保持）
      - 差分取得・保存・品質チェックの設計思想を反映
      - jquants_client 経由での取得・保存を想定
    - データベース関連ユーティリティ（テーブル存在確認、最大日付取得など）を実装
  - src/kabusys/data/__init__.py と etl/pipeline の再エクスポート

- DB / 運用上の実装上の注意点（ドキュメント的記述）
  - DuckDB を利用する想定（型は DuckDBPyConnection）
  - 各モジュールでルックアヘッドバイアス回避を明示（datetime.today()/date.today() を直接参照しない設計）
  - DuckDB の executemany の制約（空リスト不可）に配慮した実装
  - 多くの処理で冪等性（DELETE→INSERT / ON CONFLICT）を意識している

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes / 開発者向けメモ
- OpenAI 呼び出し箇所はテスト容易性のため _call_openai_api をモジュール単位に実装しており、unit test では patch して差し替え可能
- .env パースの挙動（クォート、エスケープ、コメント）は POSIX シェル風の挙動に寄せているが、特殊ケースはプロジェクトの .env.example に従うこと
- 環境変数の必須項目（Settings._require によるチェック）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等（不足時は ValueError を送出）

参考（公開 API の主な関数）
- kabusys.config.settings (Settings)
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_update_job / is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- kabusys.data.ETLResult

---

この CHANGELOG はコードベース（2026-03-29 時点）から機能・仕様を推測して作成しています。実際のリリースノートとして採用する場合は、リリース時の変更点・既知の問題・互換性に関する注意事項を追加で確認・編集してください。