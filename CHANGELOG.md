# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

リリースは逆順（最新が上）で記載しています。

## [Unreleased]

- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。主な内容は以下の通りです。

### 追加 (Added)

- パッケージ初期化
  - `src/kabusys/__init__.py` にてパッケージメタ情報を公開（バージョン: 0.1.0）。パッケージの公開モジュール: data, strategy, execution, monitoring。

- 環境設定 / ロード
  - `src/kabusys/config.py`
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動 .env ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサの実装（export 形式、引用符とエスケープ、行末コメント対応など）。
    - 必須環境変数取得用の `_require`、環境検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live / is_paper / is_dev）。
    - デフォルト値（例: KABU_API_BASE_URL、DUCKDB_PATH など）を設定。

- AI / ニュース NLP
  - `src/kabusys/ai/news_nlp.py`
    - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメント解析。
    - タイムウィンドウ算出（JST基準の前日15:00〜当日08:30相当のUTC変換）。
    - 銘柄ごとに記事を集約し、1チャンクあたり複数銘柄をバッチ（最大20銘柄）で送信。
    - API リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分成功時の部分的な DB 更新（安全性配慮）。
    - テスト容易性のため API 呼び出しを差し替え可能な実装（内部 _call_openai_api を patch で置換）。

  - `src/kabusys/ai/regime_detector.py`
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定するロジック。
    - DuckDB からのデータ取得、MA200 比率計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、スコア合成、冪等な market_regime テーブル書き込みを実装。
    - API 障害時に macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - OpenAI API 呼び出しに対するリトライ／エラーハンドリング実装。

- データ管理（Data Platform）
  - `src/kabusys/data/calendar_management.py`
    - JPX カレンダー管理（market_calendar）用ユーティリティ。
    - 営業日判定、前後営業日の取得、期間内営業日リスト取得、SQ日判定。
    - DB 記録がない場合の曜日ベースフォールバック、最大探索日数制限、冪等な calendar_update_job（J-Quants から差分取得して保存）を実装。

  - `src/kabusys/data/pipeline.py` / `src/kabusys/data/etl.py`
    - ETL 用パイプラインの基盤を実装。
    - 差分更新、バックフィル、品質チェック呼び出しの考慮。
    - ETL 実行結果を表現する `ETLResult` データクラス（品質問題・エラーの集約、辞書化ユーティリティ）。

  - `src/kabusys/data/__init__.py`
    - ETLResult を公開するための re-export（`etl.py` 経由で pipeline の ETLResult を公開）。

  - jquants クライアント参照
    - カレンダー更新や ETL で J-Quants クライアント（`kabusys.data.jquants_client`）を利用する設計。

- リサーチ / ファクター計算
  - `src/kabusys/research/factor_research.py`
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、20日平均売買代金、出来高比率、バリューファクター（PER/ROE）を DuckDB 上の SQL と Python で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足に対する安全な取り扱い（十分な履歴がない場合は None を返す等）。
    - DuckDB に依存するが、外部取引・発注 API にはアクセスしない設計。

  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証）、IC（Information Coefficient）計算（Spearman 相関に基づく rank 相関）、ランク関数（同順位は平均ランク）、ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない純 Python 実装。

- ロギング / エラーハンドリング
  - 各モジュールで詳細なログ出力を行い、DB 書き込み失敗時のロールバック処理や API エラーの挙動（リトライ・フォールバック）を明確に実装。

### 変更 (Changed)

- 初回リリースのため特記する変更はありません（新規実装）。

### 修正 (Fixed)

- 初回リリースのため特記事項はありません。

### 既知の制限 / 設計上の注意点

- DuckDB を前提とした設計であり、特定の DuckDB バージョン依存の挙動（executemany の空リスト不可等）を考慮した実装が含まれます。
- OpenAI API 呼び出しは外部サービス依存。API キーは引数または環境変数（OPENAI_API_KEY）で提供する必要があります。API失敗時はフェイルセーフ（0.0スコアやスキップ）で継続しますが、精度に影響する可能性があります。
- 日付処理はルックアヘッドバイアス防止のため内部で date.today() / datetime.today() を直接参照しない設計が採られています（target_date を明示的に渡す必要があります）。
- 一部モジュール（strategy, execution, monitoring）はパッケージ公開対象に含まれているものの、今回供給されたコードには具体的な実装ファイルが含まれていません（今後の実装予定）。

---

メンテナンスやバグ修正、API 仕様変更等の理由により将来的に Breaking change が発生する可能性があります。各リリースでは上記形式で変更点を明確に記載します。