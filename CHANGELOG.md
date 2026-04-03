# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

なお、本CHANGELOGはコードベースの内容から推測して作成しています。

## [Unreleased]

### 追加予定 / 検討中
- ドキュメントの充実（各モジュールの使用例・API仕様）
- 単体テスト・CI の追加（OpenAI クライアント等のモック例を整備）
- パッケージ配布（PyPI）向けのビルド/配布手順の整備

---

## [0.1.0] - 2026-04-03

初回公開リリース。システムは日本株のデータ収集・特徴量生成・AIベースのニューススコアリング・市場レジーム判定・マーケットカレンダー管理を中心とした以下の機能を提供します。

### 追加（Added）
- パッケージ基本情報
  - kabusys パッケージの初期公開（version = 0.1.0）。
  - public モジュール: data, research, ai, strategy, execution, monitoring（__all__ に含めて公開）。

- 設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - export KEY=val 形式やクォート・エスケープ、行末コメント等を考慮した .env パーサ実装。
  - 環境変数取得ヘルパ（Settings クラス）を提供。必須値チェック（_require）および各種設定プロパティ（DB パス、API トークン、監視閾値、環境/ログレベル判定等）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いた銘柄単位のニュース集約ロジック。
  - OpenAI（gpt-4o-mini）を用いたバッチ式センチメントスコアリング。
  - チャンク処理（最大 20 銘柄/リクエスト）、記事数・文字数上限のトリム機能。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results キー・型チェック、未知コード無視、数値クリップ）。
  - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
  - スコアを ai_scores テーブルへ冪等的（DELETE→INSERT）に書き込む処理。
  - テスト容易性のため _call_openai_api を差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム判定（bull/neutral/bear）を行う機能。
  - prices_daily と raw_news を参照して ma200_ratio とマクロ記事を取得。OpenAI 呼び出しのフェイルセーフ（失敗時 macro_sentiment=0.0）。
  - レジームスコア計算、閾値判定、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - OpenAI 呼び出しのリトライ/エラー分類処理（5xx 再試行等）。
  - news_nlp との疎結合（_call_openai_api を独立実装）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算（データ不足時の扱いを明示）。
    - calc_volatility: 20日 ATR（平均）、相対ATR、平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS=0 は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的な SQL で取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）による IC 計算。
    - rank, factor_summary: ランク化・統計サマリ計算ロジックを提供。
  - 結果は (date, code) ベースの dict リストで返す設計（DuckDB を想定）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を元に営業日判定・次/前営業日取得・期間内営業日リスト取得・SQ判定を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日）を利用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー概要等を含む）。
    - ETL パイプライン方針を反映した差分取得・保存・品質チェックのための基盤を実装（jquants_client / quality と連携想定）。
    - データ未取得時の初期ロード開始日やバックフィル設定等の定数定義。

- 汎用 / 実装方針
  - DuckDB を想定した SQL 実装で高速に集計・ウィンドウ集計を実行。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照しない（関数引数の target_date を基準にする）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定、トランザクション管理）。
  - OpenAI 呼び出し部分はテスト時の差し替えを考慮した作り。
  - ロギング（logger）を各モジュールに導入し、エラー/ワーニング/情報を出力。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 既知の制限 / 注意点（Known issues / Notes）
- OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY に依存。未設定時は ValueError を送出する箇所あり。
- news_nlp / regime_detector は API 失敗時にフェイルセーフとしてスコア 0.0 を使用する設計だが、部分的にスキップされた銘柄が発生する可能性あり。
- DuckDB の executemany に空リストを渡せない制約への対応が実装されている（空チェックを事前に行う）。
- market_calendar がまばらにしか登録されていない場合、未登録日は曜日フォールバックを使用するため厳密な市場休日判定には事前データ投入が必要。
- 外部依存（OpenAI SDK、J-Quants クライアント、DuckDB）については環境セットアップが必要。

### テスト / 開発向けのフック
- OpenAI 呼び出し箇所（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）を unittest.mock.patch 等で差し替え可能にしてあり、単体テスト作成を容易にしている。

---

開発・運用で発見された変更点や不具合は本ファイルに逐次追記します。リリース間の互換性や致命的な不具合が見つかった場合は Breaking changes として明示します。