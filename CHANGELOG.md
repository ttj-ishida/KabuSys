CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトの初回リリースに相当する内容を、ソースコードから推測してまとめています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）で列挙しています。
- リリース日はソース解析時点の日付を付与しています。

[Unreleased]
-------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

Added
- 基本パッケージとバージョン情報を導入
  - パッケージ初期化: kabusys.__version__ = "0.1.0"、主要サブパッケージを __all__ で公開。
- 環境設定管理モジュールを実装（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（優先順: OS環境変数 > .env.local > .env）。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティとバリデーションを実装。
  - 必須環境変数未設定時は明示的に ValueError を送出する _require() を提供。
- AI/NLP モジュールを実装（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）にバッチ送信。
    - JSON Mode を期待しつつ、前後ノイズが混入した場合の復元ロジック（最外の {} を抽出）を実装。
    - バッチサイズ、1銘柄当たりの最大記事数/文字数（肥大化対策）、リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ、レスポンス検証、スコア ±1.0 クリップ。
    - DuckDB へは部分置換（対象コードのみ DELETE → INSERT）で安全に書き込み。
    - テスト用に _call_openai_api を patch して差し替え可能な設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news 参照、OpenAI 呼び出しの堅牢なリトライ処理、API 失敗時はマクロセンチメントを 0 にフォールバック。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - LLM 呼び出しは news_nlp と独立した内部実装（モジュール結合回避）。
- データプラットフォーム関連モジュールを実装（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - DB 未登録日は曜日ベースのフォールバック（週末土日非営業）を一貫して使用。
    - calendar_update_job を実装し J-Quants API（jquants_client）から差分取得・バックフィル・保存を行う。
    - 最大探索日数や健全性チェック（将来日付の異常検出等）を導入。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入（取得・保存件数、品質問題、エラー集約等を含む）。
    - 差分取得、backfill、保存（idempotent）および品質チェックを想定した設計。
    - DuckDB の制約（executemany の空リスト不可等）に配慮した実装。
  - pipeline の ETLResult を kabusys.data.etl で再エクスポート。
- リサーチモジュールを実装（kabusys.research）
  - factor_research: calc_momentum / calc_value / calc_volatility を実装。DuckDB のウィンドウ関数を活用し、モメンタム・バリュー・ボラティリティ/流動性系の因子を算出（結果は date, code を含む dict のリスト）。
  - feature_exploration: calc_forward_returns（任意ホライゾンの将来リターン算出）、calc_ic（スピアマンのランク相関を実装）、rank（同順位は平均ランク）および factor_summary（count/mean/std/min/max/median）を実装。
  - research.__init__ で主要関数をエクスポート。
- ロギングとフォールバック設計
  - 各モジュールで詳細な情報・警告ログを出力。入力不足や API 例外時はフェイルセーフ（多くはスキップ/デフォルト値採用）を採用して処理の継続性を確保。
- テスト容易性の考慮
  - OpenAI 呼び出し等を差し替え可能にしてユニットテストでのモッキングを想定した実装（内部関数の patch を想定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報（OpenAI API キー等）は Settings 経由で環境変数から取得し、コード内に埋め込まない設計。
- .env ファイル読み込みで OS 環境変数を保護（既存キーは上書きしない / protected set）する仕組みを導入。

Notes / 既知の制限・今後の改善提案
- 実行・監視・戦略サブパッケージ（execution, monitoring, strategy）は __all__ に含まれているが、このスナップショットには実装ファイルが含まれていません。今後の追加を想定。
- OpenAI を用いる機能は API キー必須。キー未設定時は ValueError を発生させるため、実運用前に環境変数 OPENAI_API_KEY を設定する必要があります。フォールバックは一部処理で提供（例: macro_sentiment=0.0）があるが、基本的にはキーの提供が前提です。
- DuckDB のバージョン依存の挙動（リスト型バインド、executemany の空リスト扱い等）をコード中で考慮していますが、運用環境の DuckDB バージョンでの動作確認を推奨します。
- news_nlp/regime_detector の LLM 応答は JSON を想定して厳密にパースする設計だが、LLM の予期せぬ出力に備えた保護ロジック（JSON 抽出や無効レスポンスのスキップ）を入れています。応答フォーマット安定化のためプロンプト/モデルのチューニングが今後必要となる可能性があります。
- ai モジュールは gpt-4o-mini を想定した設計（response_format={"type":"json_object"} を使用）。モデル変更時の互換性確認が必要。

参考（実装上の重要設計ポイント）
- ルックアヘッドバイアス防止のため、日付計算は target_date を明示的に受け取り内部で date.today() を直接参照しない設計。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT 相当の処理を利用）。
- API 呼び出しはリトライ＋指数バックオフを採用し、一定回数失敗した場合は適切にロギングしてデグレード動作へフォールバック。
- DuckDB の窮屈な点（executemany の空パラメータ等）に対してガード節を入れているため、部分失敗時も既存データを過度に消さない設計。

以上。