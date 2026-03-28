# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog に準拠しています。  

## [0.1.0] - 2026-03-28

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: `kabusys`（__version__ = 0.1.0）
  - 公開 API の初期セットを定義（data, research, ai, config などを含むモジュール群を提供）。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を自動読み込みする機能を追加。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサは次をサポート:
    - 空行・コメント行（先頭 `#`）無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い。
    - クォート無しの値では `#` の直前が空白・タブの場合をコメントと認識。
  - 環境変数上書きの制御（override / protected set）を実装（OS 環境変数保護）。
  - `Settings` クラスを提供し、型付きプロパティ経由で設定を取得:
    - J-Quants / kabuステーション / Slack / DB パス等の設定項目を整備。
    - `env` / `log_level` の検証と便利なブールプロパティ (`is_live`, `is_paper`, `is_dev`)。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン（`kabusys.data.pipeline`）
    - 差分取得・保存・品質チェックを想定した ETL の骨格を実装。
    - 結果格納用の `ETLResult` データクラスを公開（`kabusys.data.etl` 経由で再エクスポート）。
  - 市場カレンダー管理（`kabusys.data.calendar_management`）
    - JPX カレンダー更新ジョブ `calendar_update_job` の実装（J-Quants クライアント経由で差分取得し冪等保存）。
    - 営業日判定・前後営業日検索・期間内営業日リスト取得のユーティリティを提供。
    - DB にデータがない場合は曜日ベースのフォールバックを採用し、部分的にしかカレンダーがない場合でも一貫して動作する設計。
    - 最大探索範囲やバックフィル、健全性チェックを実装して無限ループや極端なデータを防止。

- 研究用／ファクター計算（`kabusys.research`）
  - Factor 計算（`factor_research.py`）
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）。
    - DuckDB のウィンドウ関数を活用した SQL 主導の実装。返却は (date, code) をキーとする dict のリスト。
  - 特徴量探索（`feature_exploration.py`）
    - 将来リターン計算（`calc_forward_returns`）: 複数ホライズンに対応、入力検証あり。
    - IC（Information Coefficient）計算（`calc_ic`）: スピアマンランク相関を実装（3 レコード未満は None）。
    - ランク変換（`rank`）、ファクター統計サマリー（`factor_summary`）を実装。
    - pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。

- AI / 自然言語処理
  - ニュースセンチメント（`kabusys.ai.news_nlp`）
    - raw_news, news_symbols テーブルを利用し、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ送信、銘柄ごとの ai_score を `ai_scores` テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大対策（記事数・文字数の上限）、API レスポンスのバリデーション/クリッピング（±1.0）。
    - 再試行ロジック（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。API の致命的な失敗はスキップして継続（フェイルセーフ）。
    - JSON mode のレスポンス取り扱いと復元ロジック（前後の余計なテキストが混入した場合に最外の {} を抽出）。
    - テスト容易性のため OpenAI 呼び出し関数を patch できるように分離（_call_openai_api を内部で定義）。
    - ルックアヘッドバイアス防止のため内部で date.today() を参照しない設計。タイムウィンドウ計算は `calc_news_window` を利用。
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して `market_regime` テーブルへ冪等書き込み。
    - マクロニュースは `news_nlp.calc_news_window` と raw_news からフィルタして取得。OpenAI の呼び出しは専用の内部実装を使用しモジュール結合を避ける。
    - OpenAI API に対するリトライ・フェイルセーフ動作（失敗時は macro_sentiment=0.0）。
    - DuckDB を用いた計算・書き込み（BEGIN/DELETE/INSERT/COMMIT による冪等保存）。
    - レジームスコア合成の定義（重み・閾値）を定数で明確化。

- 依存・実装上の注意点
  - DuckDB を主要なローカルデータストアとして利用（SQL を多用）。
  - OpenAI SDK（Chat Completions）を利用する実装。API キーは引数注入可能（テスト容易性）。
  - Slack / kabuAPI / J-Quants などの外部サービス設定用の環境変数を Settings 経由で管理。

### 修正 (Fixed)
- 初期実装のため該当なし（将来的なバグ修正は個別に記載予定）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーなどのシークレットは環境変数経由で管理することを前提。誤ってコミットしないこと。
- .env を自動で読み込む仕組みを有効にしているため、開発中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑止可能。

---

注:
- 実装にはテスト用に差し替え可能なポイント（例: `_call_openai_api` を patch して API 呼び出しをモック）が複数用意されています。ユニットテスト作成時はこれらを活用してください。
- 本 CHANGELOG はソースコードの実装内容から推測して作成した初期の変更履歴です。実際のリリースで外部に公開する際は、リリースノートの追記・修正を行ってください。