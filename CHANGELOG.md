# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
現在のリリース履歴は以下のとおりです。

全般
- リリース日表記は YYYY-MM-DD 形式を使用しています。
- DuckDB を主要なローカル分析ストレージとして使用する設計になっています。
- OpenAI（gpt-4o-mini）をニュースセンチメント評価に利用する機能が含まれます。

参考: https://keepachangelog.com/ (日本語訳に沿って要約しています)

## [0.1.0] - 2026-03-31
初回リリース。

### 追加
- パッケージ初期化
  - kabusys パッケージを公開。バージョンは `0.1.0`。
  - __all__ に ["data", "strategy", "execution", "monitoring"] を定義（外部公開 API の意図を示す）。
- 設定管理 (`kabusys.config`)
  - .env ファイル（.env / .env.local）と OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パースの独自実装:
    - コメント行・空行・`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理を考慮。
    - クォートなしの値内コメント判定（直前がスペース/タブの場合のみ）。
  - 環境変数保護機能（既存 OS 環境変数を protected として上書き回避）。
  - Settings クラスを通じた型付きプロパティ提供:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ。
    - env / log_level の検証（許容値チェック）。
    - duckdb/sqlite パスは Path 型で返却。
    - 必須値未設定時は明確な ValueError を送出。
- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - ニュース記事の銘柄別センチメントを計算して `ai_scores` テーブルへ書き込む機能を実装。
  - 処理概要:
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換して使用。
    - news_symbols と raw_news を結合して銘柄ごとに最新記事を集約（1 銘柄あたり最大記事数・文字上限でトリム）。
    - 最大 _BATCH_SIZE (=20) 銘柄ごとに OpenAI にバッチ送信。
    - レスポンスは JSON Mode を期待し、厳密な JSON をパースしてスコアを抽出。
    - スコアは ±1.0 にクリップして保存。
  - エラー・安定性設計:
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスパース失敗や API エラーはログ警告の上スキップ（例外を破壊伝播させず冗長性を確保）。
    - テスト用に内部の OpenAI 呼び出し関数を patch 可能に実装。
  - DuckDB 書き込みは冪等性を重視（対象コードのみ DELETE → INSERT）かつ DuckDB の executemany の挙動に配慮。
- AI レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、`market_regime` テーブルへ書き込む機能を実装。
  - 処理概要:
    - prices_daily から過去 _MA_WINDOW (=200) 日のデータを用い、target_date 未満のデータのみで MA200 比率を算出（ルックアヘッドバイアス回避）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出し LLM に送付してマクロセンチメントをスコア化。
    - 合成スコアをクリップし閾値に従ってラベルを決定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作を行う。
  - エラー設計:
    - OpenAI 未設定時は ValueError を送出。
    - API 失敗時は macro_sentiment = 0.0 でフォールバック（フェイルセーフ）。
    - レスポンスパースエラーや API の一時障害に対するリトライを実装。
- データ処理 / ETL (`kabusys.data.pipeline`, `kabusys.data.etl`)
  - ETLResult データクラスを公開 (ETL 実行のメタ情報と品質問題/エラーを格納)。
  - 差分更新・バックフィル・品質チェック・idempotent 保存を設計方針に含むパイプラインの基盤コードを実装。
  - jquants_client 経由でのデータ取得と品質検査を想定（jquants_client は別モジュールとして呼び出し）。
- カレンダー管理 (`kabusys.data.calendar_management`)
  - JPX 市場カレンダー管理（market_calendar テーブル）を扱うユーティリティを実装。
  - 営業日判定・翌営業日/前営業日取得・期間内営業日取得・SQ 日判定などを提供。
  - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新するジョブを実装（バックフィルと健全性チェックを含む）。
  - DB にカレンダーデータがない場合のフォールバックとして曜日ベースの判定（平日=営業日）を一貫して利用。
- リサーチモジュール (`kabusys.research`)
  - Factor 計算 (`factor_research.py`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算関数を実装。
    - DuckDB 上の SQL と窓関数を活用して効率的に計算。
    - データ不足時の None 返却やログ出力を考慮。
  - Feature Exploration (`feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。
    - IC（Spearman の ρ）計算、ランク化ユーティリティ（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
- テスト／運用を考慮した設計上の注記
  - ルックアヘッドバイアス防止: 各種処理で datetime.today()/date.today() を参照しない設計（全て target_date ベースで動作）。
  - OpenAI API 呼び出し部分は patch しやすい構造にしてユニットテスト容易性を確保。
  - DuckDB 書き込みは部分失敗時に他データを保護する（書き込み対象コードを絞る等）。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 非推奨
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### セキュリティ
- OpenAI API キー等の機密情報は環境変数経由で取得する設計。ただし、運用時は追加のシークレット管理を推奨。

注記・今後の課題（実装方針のメモ）
- strategy / execution / monitoring といった名前が package __all__ に含まれているため、それらのモジュール（自動売買ロジック・発注実行・監視機能）は今後の実装予定。または別パッケージ化の可能性あり。
- jquants_client や quality モジュール等の外部依存モジュール（実際の API クライアントや品質チェック実装）が別途必要。現在のコードはそれらを呼び出すインターフェースを提供。
- 本リリースは機能実装に重点を置いた初版であり、運用パイプライン・監視・権限管理等の実運用要件は継続して強化予定。

もし CHANGELOG に記載してほしい追加の観点（例: 期待する利用シナリオ、リリースノートに含めたい注意点、特定ファイル/関数の詳細など）があれば教えてください。必要に応じて追記・修正します。