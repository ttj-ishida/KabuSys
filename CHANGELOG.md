Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての変更は semver 準拠で管理します。初期リリースの内容をコードベースから推測して記載しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開サブモジュールは data, strategy, execution, monitoring。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ強化:
    - export KEY=val 形式対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント処理等。
  - 環境変数保護機構 (protected keys) を考慮した上書きロジック。
  - Settings クラスを提供（プロパティベース）:
    - J-Quants / kabu API / LINE / データベース（DuckDB/SQLite） / 監視設定（PID, kill フラグ, リソース閾値）/ システム環境（env, log_level）等の取得とバリデーション。
    - KABUSYS_ENV の許容値チェック（development, paper_trading, live）。
    - LOG_LEVEL の許容値チェック。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
  - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
  - バッチ処理（最大 20 銘柄／API 呼び出し）、記事トリム（文字数・記事数上限）を実装。
  - API 呼び出しはリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフを実装。失敗時はスキップ（フェイルセーフ）。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、コード整合性、スコア数値化、±1.0 でクリップ）。
  - テスト容易性のために _call_openai_api を差し替え可能に設計。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定するロジックを実装。
  - マクロキーワードで raw_news をフィルタして OpenAI に投げる実装、API リトライ＆フォールバック（API 失敗時は macro_sentiment=0.0）。
  - レジームスコア合成、閾値判定、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）での書き込み。
  - lookahead バイアスを防ぐ設計（date 未満のデータのみ参照、datetime.today() を直接参照しない）。
  - テスト用に _call_openai_api の差し替えを想定。

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。最大探索日数制限で無限ループ回避。
    - JPX カレンダーを J-Quants API から差分取得して更新する calendar_update_job（バックフィル、健全性チェック、ON CONFLICT 相当の冪等保存を想定）。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧などを含む）。
    - 差分更新、backfill、品質チェック（quality モジュール連携）、idempotent な保存方針を想定した設計。
    - ETLResult を外部公開（src/kabusys/data/etl.py で再エクスポート）。
  - その他ユーティリティ: テーブル存在チェックや日付処理用ユーティリティを実装。

- リサーチ（src/kabusys/research/*）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR, ATR_pct）、流動性（20日平均売買代金、volume_ratio）、バリュー（PER, ROE）等のファクター計算関数を実装。DuckDB を用いた SQL 集約 + Python 結果返却の設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付け（rank）、統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を公開。data.stats の zscore_normalize を再利用。

Changed
- （初版のため過去バージョンからの変更なし）

Fixed
- （初版のため既知のバグ修正履歴なし。ただし各モジュールにログ出力・フォールバック・例外処理を多数実装し堅牢化を図っている旨を注記）

Security
- OpenAI API キーの取り扱いは引数優先 → 環境変数参照の順序で設計。必須未設定時は明示的な ValueError を発生させることで安全設計を確保。

Notes / 設計上の重要点
- ルックアヘッドバイアス防止: AI / リサーチ処理は内部で datetime.today()/date.today() を直接参照せず、外部から target_date を注入して determinism を保つ設計。
- DuckDB を主要なローカル分析 DB として想定。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用し、レスポンスパースの冗長ケース（前後テキスト混在など）に対する回復処理を実装。
- テスト容易性: OpenAI 呼び出し部分の差し替え (unittest.mock.patch) を前提とした設計を各 ai モジュールに導入。
- .env パーサは多くの実運用ケース（export プレフィックス、クォート内エスケープ、コメント）に対応。

今後の予定（例）
- strategy / execution / monitoring の実装・統合テスト
- 更なる品質チェック・監視アラートの充実
- ドキュメント & サンプル ETL 実行手順の追加

その他
- 実装はコードコメント・docstring に基づいて推測して記載しています。実際の挙動や API 仕様は実運用時に確認してください。