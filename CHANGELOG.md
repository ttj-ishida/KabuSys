CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現時点ではリリース済みの初期バージョンのみ存在します）

[0.1.0] - 2026-03-31
-------------------

初回リリース。以下の主要機能と実装方針を含みます。

Added
- パッケージ初期構成
  - kabusys パッケージの公開モジュール指定（data, strategy, execution, monitoring）。
  - バージョン情報: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export prefix、クォート（シングル/ダブル）、エスケープ、インラインコメントを考慮した堅牢なパーサ。
  - 必須変数取得ヘルパー (_require) と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニューススコアリング（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの最大記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証と数値クリッピング（±1.0）。
    - テスト用のモック差替えポイント（_call_openai_api）。
    - 時間ウィンドウ計算（JST を基準に UTC naive datetime を返す calc_news_window）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）判定。
    - DuckDB からのデータ参照、OpenAI 呼び出し（gpt-4o-mini）とリトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - 計算結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易化のためモック差替えポイントあり。

- データ基盤ユーティリティ（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）および is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 登録値優先の一貫した判定ロジック、検索範囲の安全上限。
    - J-Quants クライアント経由での差分取得と冪等保存のフロー。
  - ETL パイプライン（pipeline）
    - 差分取得、保存（jquants_client の save_* を用いた冪等保存）、品質チェック（quality モジュール）を含む ETLResult データクラス。
    - ETLResult による処理メタ情報（取得件数、保存件数、品質問題、エラー一覧）を保持。
    - 市場カレンダー先読み・バックフィル挙動、最小データ日付やバックフィル既定値を実装。
  - etl モジュールから ETLResult を再エクスポート。

- 研究用ユーティリティ（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility
    - モメンタム（1/3/6ヶ月リターン、MA200乖離）、ボラティリティ（20日ATR、相対ATR、20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を用いて計算。
    - データ不足時は None を返す挙動。
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
    - 将来リターン計算（複数ホライズン対応、入力検証）、Spearmanランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティ。
  - zscore_normalize を data.stats から再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出して誤動作を防止。

Notes / 設計上の注意
- ルックアヘッドバイアス対策
  - 各 AI/研究機能は datetime.today()/date.today() を内部参照せず、必ず引数で渡された target_date を基準に処理します。
  - DB クエリは target_date より前（排他）や LEAD/ LAG を用いた適切な窓で参照し、将来情報を参照しないように設計されています。

- データベース
  - デフォルトの DuckDB パス: data/kabusys.duckdb（Settings.duckdb_path）、SQLite（監視用）: data/monitoring.db。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装あり。

- 冪等性
  - ETL / calendar 更新 / ai スコア書き込み等は既存レコードを削除してから挿入する方式などで冪等性を確保。

- テストのためのフック
  - OpenAI 呼び出しを差し替えられる内部関数（_call_openai_api）を各モジュールに用意しており、ユニットテストでモックが可能。

- 環境変数（主要）
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルト: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL
  - 自動 .env ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

Migration / Upgrade Notes
- 初回リリースのためマイグレーション不要。ただし本リポジトリを導入する際は .env.example を参照して必要な環境変数を設定してください。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キーを必要とするため、呼び出し前に OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。

既知の制限
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。
- strategy / execution / monitoring の実装は本リリースではコードベースへのエントリが宣言されているのみで、具体的な注文実行ロジックや監視ワークフローは本稿でカバーされていません（将来のリリースで追加予定）。

貢献
- 初期実装に含まれるモジュール群について、今後の改良（性能改善、追加指標、運用監視強化）を歓迎します。