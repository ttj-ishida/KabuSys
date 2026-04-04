# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理されています。

リンクや詳細な履歴はリポジトリ内の該当モジュールの docstring を参照してください。

## [0.1.0] - 2026-04-04

初回リリース — KabuSys のコア機能を実装しました。主にデータプラットフォーム、研究用ユーティリティ、AI によるニュースセンチメント評価、環境設定の取り扱いなどを含みます。

### Added
- 基本パッケージ構成
  - pakage エントリポイント: `src/kabusys/__init__.py` によりバージョン `0.1.0` と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理モジュール
  - `kabusys.config.Settings`
    - .env 自動読み込み機能を実装（プロジェクトルート判定: `.git` または `pyproject.toml`）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - .env パーサ実装: export プレフィックス対応、クォート内エスケープ処理、行内コメント判定など、実用的なパース挙動
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
    - 各種パス・閾値・運用フラグ (DuckDB/SQLite パス、PID/KILL フラグファイルパス、CPU/MEM/DISK閾値、ログレベル / 環境モード判定) をプロパティとして提供

- AI ニュース NLP（センチメント）モジュール
  - `kabusys.ai.news_nlp.score_news`
    - raw_news / news_symbols を集約して銘柄単位に記事を結合
    - OpenAI（gpt-4o-mini, JSON mode）を用いたバッチ評価（最大20銘柄/チャンク）
    - レスポンスの厳密なバリデーションと JSON 復元ロジック（前後余分テキストが混入した場合の復旧）
    - リトライ戦略（429/ネットワーク/タイムアウト・5xx に対する指数バックオフ）
    - スコアは ±1.0 にクリップして `ai_scores` テーブルへ冪等置換（DELETE → INSERT）
    - テスト容易性のため OpenAI 呼び出しは差し替え可能（単体テスト用の patch を想定）
    - タイムウィンドウ計算ユーティリティ `calc_news_window(target_date)` を提供（JST ベースで前日 15:00 〜 当日 08:30 相当）

- 市場レジーム判定モジュール
  - `kabusys.ai.regime_detector.score_regime`
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来の LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出
    - OpenAI 呼び出し（gpt-4o-mini, JSON mode）を利用、API エラー時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）
    - DuckDB を用いたデータ取得と `market_regime` テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス対策として日時の直接参照を行わない実装（target_date 未満のみ参照）

- Data モジュール（DuckDB ベースのデータ層）
  - カレンダー管理: `kabusys.data.calendar_management`
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job`
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した振る舞い
    - 最大探索日数制限・バックフィル・健全性チェックを実装
  - ETL パイプライン: `kabusys.data.pipeline`
    - ETL の結果を表すデータクラス `ETLResult` を公開（品質チェック結果・エラーメッセージを含む）
    - 差分取得、バックフィル、品質チェックフローの基礎設計
  - ETL 公開インターフェースの再エクスポート: `kabusys.data.etl.ETLResult`

- Research（因子・特徴量解析）モジュール
  - `kabusys.research.factor_research`
    - モメンタム: `calc_momentum`（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ / 流動性: `calc_volatility`（20日 ATR、相対 ATR、平均売買代金、出来高比）
    - バリュー: `calc_value`（PER, ROE の計算。最新財務データの取得ロジック含む）
    - DuckDB を使った SQL ベースの効率的な実装（外部取引・発注 API へはアクセスしない）
  - `kabusys.research.feature_exploration`
    - 将来リターン計算: `calc_forward_returns`（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算: `calc_ic`（Spearman ランク相関）
    - 統計サマリー: `factor_summary`（count, mean, std, min, max, median）
    - ランク変換ユーティリティ `rank`
    - 外部依存無し（pandas 等に依存しない純標準ライブラリ実装）

- ロギングとフェイルセーフ設計
  - 多くの処理で問題発生時に例外を投げずログに警告を残して継続するフェイルセーフを採用（部分失敗による全体停止の回避）
  - DuckDB に対する互換性考慮（executemany の空リスト回避等）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 `OPENAI_API_KEY` にも対応。キー未設定時は明示的に ValueError を発生させ、誤動作を抑止。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: ニュース収集や指標算出で internal な現在時刻参照（datetime.today()/date.today()）を直接使用しない設計。全て target_date を明示的に受け取り、その日未満のデータのみ参照する。
- OpenAI 呼び出しはモジュール内でラップしており、単体テストで差し替えやすい設計（patch によるモックが想定されている）。
- DB 書き込みは冪等性（同一日付の置換）を意識して実装されているため、再実行に耐える設計。
- .env パーサは現実的な .env 表記（export, シングル/ダブルクォート、エスケープ、インラインコメント）に対応。

---

今後のリリースで予定していること（例）
- strategy / execution / monitoring サブパッケージの具体的なアルゴリズムと実行ロジックの実装
- CI 用のテストカバレッジ拡充（OpenAI 呼び出しのモック・DuckDB テストフィクスチャ）
- ドキュメントの追加（各モジュールの使用例・API リファレンス）

もし特定の変更点の表現や詳細（フォーマット・日付など）に修正が必要であればお知らせください。