# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
現在のパッケージバージョン: 0.1.0

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買・データ基盤・リサーチ・AI補助モジュール群を提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ外部公開モジュール候補を __all__ に定義（"data", "strategy", "execution", "monitoring"）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理）。
  - 読み込み時に OS 環境変数を保護する protected セットを導入（.env の上書きを制御）。
  - 必須環境変数チェック用の _require ユーティリティと、env/log level のバリデーション（許容値チェック）を実装。
  - デフォルト値：KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH など。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄毎にニュースを組み、OpenAI（gpt-4o-mini）でセンチメントスコアを生成。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたりの記事数制限（最大 10 件）、文字数トリム（_MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode を使った厳格なレスポンス期待、レスポンスのバリデーションと部分的な安全性（未知コード無視、数値チェック、±1.0 でクリップ）。
    - リトライ戦略（429・接続断・タイムアウト・5xx に対して指数バックオフ）とフェイルセーフ（失敗時はスキップして処理継続）。
    - DuckDB 互換性を考慮した書き込み（部分成功時に他コードの既存スコアを保持するため DELETE → INSERT の個別 executemany を採用、空パラメータの扱いに配慮）。
    - 時間ウィンドウ計算ユーティリティ calc_news_window を提供（JST 前日 15:00 〜 当日 08:30 のウィンドウを UTC naive datetime で返す）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはニュースタイトルをマクロキーワードでフィルタし、OpenAI へ渡して JSON レスポンスから macro_sentiment を抽出。
    - API 呼び出しのリトライ、例外処理、JSON パース失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 計算結果は冪等に market_regime テーブルへ保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - ルックアヘッドバイアス防止の設計（内部で date.today() を参照しない、DB クエリは target_date 未満の排他条件を使用）。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定・前後営業日検索・期間内営業日列挙機能を追加。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（土日を非営業日扱い）。
    - next_trading_day / prev_trading_day は探索上限 (_MAX_SEARCH_DAYS) を設けて無限ループを防止。
    - JPX カレンダーを J-Quants API から差分取得して更新する calendar_update_job を実装（バックフィル、健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline, etl）
    - ETLResult dataclass を提供（各種取得・保存数や品質問題、エラーの集約）。
    - 差分取得・保存・品質チェックを行う基盤設計（J-Quants クライアント連携想定）。
    - テーブル最大日付取得、テーブル存在確認などのユーティリティを実装。
    - backfill_days による再取得や、品質チェックを継続的に収集する方針を取る。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ATR（20日）、平均売買代金/出来高比率などの計算関数を追加。DuckDB を用いた SQL 実装。
    - データ不足時の None 返却、営業日ベースのホライズン設計、MA 等の行数チェックを実施。
  - 特徴量探索/評価（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、リード/ラグを利用した1クエリ実装）。
    - IC（Spearman ρ）計算、rank（同順位は平均ランク）ユーティリティ。
    - factor_summary：count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリー。

### Changed
- （初回リリースのため該当なし）

### Fixed
- DB 書き込み失敗時の安全処理
  - market_regime / ai_scores 書き込みで例外発生時に ROLLBACK を試み、ROLLBACK 自体の失敗もログ出力して上位へ例外を伝達するように実装（部分失敗でも既存データを保護するための実装上の配慮）。
- OpenAI レスポンスの堅牢なパース
  - JSON mode でも前後に余計なテキストが混ざるケースに対応するため、最外の {} を抽出して再パースするフォールバックを導入。

### Security
- 環境変数の取り扱いに注意
  - OS 環境変数は自動 .env ロード時に protected として上書きされないよう保護。
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY にて注入可能。未設定時は ValueError を送出して誤使用を防止。

### Performance
- ニュース NLP のバッチ処理とチャンク化により API 呼び出し回数を制御（デフォルト 20 銘柄 / チャンク）。
- DuckDB への複数行挿入は executemany を用いるが、空リストバインドに関する互換性に対応（空パラメータは実行しない）。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、すべての「日付基準」処理は外部から与えられる target_date を使い、内部で datetime.today() / date.today() を安易に参照しない方針を徹底。
- モジュール間の結合を低く保つため、内部の OpenAI 呼び出し関数はモジュールごとに独立実装（テスト時に差し替えやすい）。
- 外部依存は最小限に抑え、DuckDB と OpenAI SDK（openai）を使用。リサーチ系ユーティリティは標準ライブラリのみで実装。

もし細かい変更点（特定ファイルの注釈や実装意図）について追記や修正が必要でしたら、その箇所を指定していただければ、CHANGELOG を更新します。