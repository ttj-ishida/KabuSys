CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。
このプロジェクトは Keep a Changelog のガイドラインに従います。
開始日: 2026-03-31

フォーマット:
- Unreleased: 次リリースのための保留中の変更
- 各バージョン: 追加（Added）/ 変更（Changed）/ 修正（Fixed）/ 削除（Removed）等で分類

Unreleased
----------
（なし）

0.1.0 - 2026-03-31
-----------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義し、主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定管理モジュール
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 行パーサ実装（コメント、export 前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
      - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/監視閾値/環境名/ログレベル等。
    - 必須環境変数未設定時は _require() による ValueError を投げる。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄別にニュースを結合し、OpenAI（gpt-4o-mini の JSON Mode）でセンチメントを評価して ai_scores テーブルへ保存する機能を提供（score_news）。
    - 時間ウィンドウ（前日15:00 JST～当日08:30 JST）計算ユーティリティ calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数/文字数制限、429/ネットワーク/タイムアウト/5xx のエクスポネンシャルバックオフリトライを実装。
    - レスポンスの堅牢なバリデーションとスコアクリップ（±1.0）、部分的書き込み（対象コードのみ DELETE → INSERT）により部分失敗時のデータ保護を実現。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch ポイントを用意）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードによる記事フィルタ、OpenAI コールのリトライ・フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため datetime.today() 等を参照しない設計。

- Research（リサーチ）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム / ボラティリティ / バリュー等の定量ファクター計算関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None を返す）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出。
    - DuckDB 上で SQL + Python により再現可能で、外部 API にアクセスしない設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリおよび DuckDB のみで動作する設計。
    - calc_forward_returns はホライズンの検証（1..252）や効率的な単一クエリ取得を行う。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- Data（データプラットフォーム）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理と営業日判定ロジックを実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar が未登録時は曜日ベース（土日）をフォールバック。
    - calendar_update_job により J-Quants API から差分取得→market_calendar 更新（バックフィル・健全性チェックあり）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL のコア（差分取得、保存、品質チェック）を管理するパイプライン実装。
    - ETLResult データクラスを導入し、fetch/save の件数や品質問題・エラー情報を集約。
    - jquants_client / quality モジュールとの連携を想定（jquants_client はデータ取得/保存の責任）。

- パッケージ API の公開方針
  - OpenAI クライアント呼び出しはモジュール内の専用関数経由で行うため、テスト時に簡単に差し替え可能（mock ポイントが明示されている）。
  - DuckDB 接続を外部から注入する設計により、副作用を抑えテスト容易性を向上。

Documentation / Design notes
- ルックアヘッドバイアス防止:
  - AI・リサーチ関連の関数は internal において date.today() を参照しないよう設計（外部から target_date を与える）。
- DB 書き込みは冪等性を重視:
  - DELETE→INSERT / ON CONFLICT DO UPDATE（保存関数側）等で部分失敗時のデータ保護を行う。
- エラー処理:
  - OpenAI 周りは 429/ネットワーク/タイムアウト/5xx をリトライし、それ以外や最終的失敗はフェイルセーフ（スコア=0 やスキップ）で継続する方針。
- テスト支援:
  - OpenAI 呼び出しを差し替えられるポイントを用意（unittest.mock.patch を想定）。
  - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notable environment variables
- 必須（Settings._require により未設定は例外）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
  - LOG_LEVEL — デフォルト "INFO"
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 存在すると自動 .env 読み込みを無効化
  - OPENAI_API_KEY — AI モジュールでの API キー（api_key 引数で上書き可能）
  - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH 等（デフォルト値あり）

Compatibility / Requirements
- DuckDB を利用する前提（DuckDB のバインド挙動に起因する注意点がコメントに記載されている）。
- OpenAI Python SDK を使用（gpt-4o-mini を想定、JSON Mode レスポンス処理を実装）。
- J-Quants クライアント連携（jquants_client モジュールと連携する設計）。

Breaking Changes
- 初回リリースのため該当なし。

Migration notes
- 既存データベースを用いる場合、required な環境変数を設定すること（特に OpenAI キーは score_news / score_regime を実行する際に必須）。
- .env / .env.local の扱い: OS 環境変数が優先され、.env.local が .env を上書きする（protected な OS 環境変数は上書かれない）。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動読込を止めること。

開発者向けメモ
- OpenAI 呼び出しの差し替え:
  - news_nlp._call_openai_api, regime_detector._call_openai_api を unittest.mock.patch してテスト可能。
- DuckDB の executemany は空リストを渡せないバージョン依存問題への対応が実装済み（empty-check を行っている）。
- レスポンスの堅牢性を担保するため、LLMレスポンスパース時のエラーは警告ログを残してスコアをフォールバックする方針。

今後
- strategy / execution / monitoring の実装を補完してエンドツーエンドな自動売買ワークフローを提供予定。
- ai モジュールのモデル/プロンプトや重みのチューニング、品質チェックの拡張を予定。

以上。