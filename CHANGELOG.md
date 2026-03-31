# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

なお、本 CHANGELOG はリポジトリ内のソースコード（docstring・実装・定数等）から機能と設計意図を推測してまとめたもので、実際のコミット履歴ではありません。

## [Unreleased]

### 修正予定 / 既知の問題
- data.pipeline._get_max_date 関数定義の末尾に不完全な実装（`return date.fro` のようなタイポ）が見つかります。現状だとテーブルが空でない場合の戻り値処理が壊れているため、修正が必要です。
- パッケージの __all__（kabusys.__init__）に strategy, execution, monitoring が含まれる一方で、その一部モジュール（または公開 API）が現時点で不足している可能性があります。今後のリリースで空のプレースホルダや未実装部分の整備を予定しています。

---

## [0.1.0] - 2026-03-31

初回公開リリース — 基本的なデータ基盤、リサーチ、AI ユーティリティを提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開サブパッケージの宣言: data, strategy, execution, monitoring（strategy 等は将来的な実装のためのプレースホルダを含む）。
- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートの検出は .git または pyproject.toml を基準に実施）。
  - 読み込みの優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサは export 形、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントを考慮した堅牢な実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値などの設定をプロパティ経由で取得。必須項目は _require() で明示的にエラーにする。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証。
- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出・ai_scores テーブルへ冪等書き込み。
    - ウィンドウ時間の計算 calc_news_window(target_date)（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換した半開区間を返す）。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄あたりの最大記事数／文字数制限、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳格なバリデーションとスコアのクリップを実装。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - kabusys.ai.regime_detector
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225 連動型）の直近 200 日 MA 乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し、API エラー時のフォールバック macro_sentiment=0.0、リトライ・エクスポネンシャルバックオフ、レスポンス JSON パースの堅牢化を実装。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみを使用し、datetime.today()/date.today() を直接参照しない設計）。
- Data / ETL（kabusys.data）
  - pipeline.ETLResult: ETL 実行結果を表す dataclass（品質問題の収集、エラー有無の判定、辞書変換メソッドを提供）。
  - data.etl: ETLResult の公開エイリアス。
  - data.pipeline: ETL パイプラインの骨格（差分更新／保存／品質チェックの設計方針を反映）。
  - calendar_management:
    - JPX カレンダー取得と市場営業日の判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の有無に応じた DB 優先ロジックと曜日ベースのフォールバック、最大探索日数の制限、夜間バッチ更新 job（calendar_update_job）および J-Quants クライアント経由の差分フェッチと冪等保存。
    - バックフィル／健全性チェック（直近の再取得、未来日付の異常検知）。
- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を prices_daily から計算。
    - calc_volatility: 20 日 ATR（true range の扱いを明確化）、相対 ATR、20 日平均売買代金・出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 または NULL のときは None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターンをまとめて取得（複数ホライズンを同一クエリで効率的に計算）。
    - calc_ic: Spearman ランク相関（IC）を実装（同順位は平均ランク）。
    - rank / factor_summary: ランク関数と基礎統計量サマリーを提供。
  - research パッケージは kabusys.data.stats の zscore_normalize を再利用する設計。
- 一貫した DB 操作設計
  - DuckDB を主要な分析 DB として使用（DuckDB 接続を関数引数で受け、prices_daily / raw_news / raw_financials / market_calendar / ai_scores / market_regime 等のテーブルを参照／更新）。
  - DB 書き込みは冪等化（DELETE→INSERT や ON CONFLICT 相当の保存）とトランザクション制御（BEGIN/COMMIT/ROLLBACK）を基本として実装。
  - executemany の空パラメータ回避など DuckDB の互換性考慮。

### Changed
- （初版リリースのため該当なし）

### Fixed
- （初版リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を期待する設計。コードはキーをログに出力しないよう想定されていますが、利用者側でもキー管理に注意してください。
- .env の自動読み込みは OS 環境変数を保護するため既存キーを保護する設計（protected set を用いる）。

### Notes / Implementation details
- ルックアヘッドバイアス防止: AI / 指標計算系の関数は date.today() を参照せず、必ず caller が target_date を与える設計になっています。
- テスト容易性: OpenAI 呼び出しポイント（_call_openai_api）や API キー注入により unittest.mock.patch 等で置き換えやすく設計されています。
- フェイルセーフ: LLM 呼び出しの失敗やレスポンスパース失敗時は例外を上げずフォールバック値（例: macro_sentiment=0.0）で継続する設計が多く採用されています（運用での頑健性を優先）。
- ロギング: 各モジュールで情報・警告・例外ログを適切に出力するよう実装されています。

---

将来的なリリース計画（想定）
- 0.2.x: pipeline の完成、ETL 実行エントリポイント、J-Quants クライアントの拡充、strategy / execution / monitoring の公開 API 実装。
- 0.3.x: モデル運用（paper/live）向けの監視・発注連携、テストカバレッジ強化、既知のタイポ・バグ修正。

もし特にフォーカスしたい変更点（例: ETL の挙動、AI のバッチロジック、.env のパース挙動など）があれば、そこを深掘りしてより詳細な変更履歴（コミット単位想定）を作成できます。どの部分を重点的に記載しますか？