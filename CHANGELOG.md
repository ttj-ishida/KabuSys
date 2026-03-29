# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  
比較可能な変更履歴は semver に準拠します。

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を実装。
  - パッケージメタ情報
    - src/kabusys/__init__.py
      - パッケージ version を "0.1.0" として公開。
      - __all__ に主要サブパッケージを列挙（data, strategy, execution, monitoring）。

  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env/.env.local の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml から検出）。
      - 読み込みルール:
        - 優先順位: OS環境変数 > .env.local > .env
        - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
        - export KEY=val 形式、シングル/ダブルクォート、エスケープ、行内コメント処理に対応。
        - override / protected 機構により OS 環境を保護しつつ .env.local で上書き可能。
      - Settings クラスを公開（settings）。主要プロパティ:
        - jquants_refresh_token, kabu_api_password, kabu_api_base_url
        - slack_bot_token, slack_channel_id
        - duckdb_path, sqlite_path（デフォルトパスを設定）
        - env, log_level（許容値のバリデーションを実装）
        - is_live / is_paper / is_dev ヘルパー

  - AI（NLP / レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを評価して ai_scores テーブルへ保存する機能を追加。
      - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を厳密に計算する calc_news_window を提供。
      - バッチサイズ、文字数上限、記事数上限などのトークン肥大化対策を組み込み。
      - JSON Mode の応答検証と復元ロジック（前後余計なテキストの切り出し）を実装。
      - 再試行ポリシー（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）とフェイルセーフ設計（失敗時は部分スキップして継続）。
      - テストしやすさのため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
      - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する機能を追加。
      - マクロニュース抽出（キーワードリスト）・OpenAI 呼び出し・再試行・パースフェイル時のフォールバック（macro_sentiment=0.0）を実装。
      - ルックアヘッドバイアス回避の設計（target_date 未満のデータのみを使用、datetime.today() を直接参照しない）。
      - score_regime(conn, target_date, api_key=None) を公開。market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

  - データ（Data Platform）
    - src/kabusys/data/calendar_management.py
      - JPX マーケットカレンダー管理ロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
      - market_calendar が未取得の場合は曜日ベースのフォールバック（週末除外）を行い、一貫性のある振る舞いを保証。
      - calendar_update_job(conn, lookahead_days=90) を提供。J-Quants クライアント経由で差分取得し、冪等保存（バックフィルと健全性チェックを含む）。
    - src/kabusys/data/pipeline.py
      - ETL パイプライン基盤を実装。
      - 差分取得、保存（jquants_client の save_* を利用）、品質チェック（quality モジュール）を想定した設計。
      - ETL 実行結果を表す dataclass ETLResult を追加（to_dict、エラー/品質判定ヘルパーを含む）。
      - 内部ユーティリティ: テーブル存在確認、最大日付取得、market calendar 用ヘルパ等。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート（公開インターフェース）。

  - Research（因子・特徴量探索）
    - src/kabusys/research/factor_research.py
      - モメンタム、バリュー、ボラティリティ／流動性の計算関数を追加。
      - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日MA乖離を計算。
      - calc_volatility(conn, target_date): 20日 ATR、ATR比、平均売買代金、出来高比率等を計算。
      - calc_value(conn, target_date): raw_financials を参照して PER / ROE を計算。
      - DuckDB を用いた SQL ベース実装で、データ不足時は None を返す設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン calc_forward_returns(conn, target_date, horizons) を追加（複数ホライズンに対応）。
      - calc_ic: スピアマンランク相関（Information Coefficient）の実装。
      - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties を考慮）。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

  - モジュール公開/再エクスポート
    - src/kabusys/ai/__init__.py: score_news を公開。
    - src/kabusys/research/__init__.py: 主要な研究用関数と zscore_normalize（外部モジュールから）を公開。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Removed
- （初回リリースのため無し）

### Notes / 実装上の重要事項
- OpenAI 関連:
  - score_news / score_regime は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
  - API 呼び出しに対する堅牢性として再試行（指数バックオフ）や失敗時のフォールバックを備え、全体処理が停止しないよう設計している。
  - テスト容易性のため、内部の _call_openai_api をモック置換して外部呼び出しを避けられる。
- DuckDB 操作:
  - 書き込みは冪等性を意識してトランザクション（BEGIN/DELETE/INSERT/COMMIT）で行う。例外時には ROLLBACK を試行し、失敗時は警告ログを出力。
  - DuckDB バージョンの制約（executemany に空リスト不可 等）に配慮した実装がある。
- ルックアヘッドバイアス対策:
  - 多くの関数（score_news, score_regime, 各種算出関数）は datetime.today()/date.today() に依存せず、引数の target_date のみを基準に計算する設計。
- 環境変数:
  - 本リリースでは J-Quants / kabu / Slack / OpenAI のトークンやパスが必須となる箇所がある（config.Settings がそれらを取得する）。
  - デフォルトのデータベースパスは settings.duckdb_path = data/kabusys.duckdb、settings.sqlite_path = data/monitoring.db。

### Known limitations / TODO
- 一部外部クライアント（jquants_client）の実装はパッケージ内で参照されているが、この差分にはクライアントの実装ファイルを含めていないため、実行時に該当実装が必要。
- strategy, execution, monitoring サブパッケージは __all__ で公開されているが、この差分では詳細実装が含まれていない（将来的な実装予定）。
- 現段階では PBR・配当利回りなどのバリューファクターは未実装（calc_value に注記あり）。

---

（今後のリリースでは Changed / Fixed / Deprecated / Removed / Security セクションを適宜使用してください。）