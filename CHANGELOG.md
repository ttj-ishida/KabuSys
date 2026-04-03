# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリは初版リリースとしてバージョン 0.1.0 を公開しています。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能とモジュールを実装しました。

### Added
- パッケージ基盤
  - パッケージ情報: `kabusys.__version__ = "0.1.0"` を設定し、主要サブパッケージ（data, research, ai, など）を公開。
- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` で検出）。
  - 読込順序: OS 環境変数 > `.env.local`（上書き）> `.env`（既存値を上書きしない）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能（テスト等で使用）。
  - .env パーサ実装: export 形式のサポート、クォートやエスケープ、行内コメントの扱いを尊重。
  - 必須キー取得ヘルパ `_require`、および Settings クラスで各種設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視設定等）。
  - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値セットを定義）。
- AI 関連 (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.py`)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へ JSON モードでバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ `calc_news_window` を実装。
    - バッチサイズ、文字数・記事数の上限、429/ネット切断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの堅牢なバリデーションを実装。
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへDELETE→INSERT（冪等書き込み）。
    - テスト容易性のため OpenAI 呼び出し箇所を置換可能に設計（`_call_openai_api` のモック）。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュース由来の LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ルックアヘッドバイアス回避設計（target_date 未満のみ使用、datetime.today/date.today を参照しない）。
    - マクロニュースはキーワードフィルタで抽出し、OpenAI（gpt-4o-mini）へ送信。API障害時はフォールバックで macro_sentiment=0.0。
    - レジームスコアを market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、ロールバック処理あり）。
- データ基盤（`kabusys.data`）
  - カレンダー管理 (`calendar_management.py`)
    - JPX カレンダー（market_calendar）に基づく営業日判定・次/前営業日計算・期間内営業日取得・SQ判定などのユーティリティを実装。
    - market_calendar が未取得の場合は曜日ベース（日曜・土曜を休業日）によるフォールバック。
    - 夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
  - ETL / パイプライン (`pipeline.py`, `etl.py`)
    - ETL のインターフェースと実行結果データクラス `ETLResult` を実装。取得件数・保存件数・品質チェック問題・エラー概要を保持。
    - 差分取得、バックフィル、品質チェックの考慮点を反映した設計（J-Quants クライアント呼び出しを想定）。
    - `data.etl` で `ETLResult` を再エクスポート。
- リサーチモジュール（`kabusys.research`）
  - ファクター計算 (`research/factor_research.py`)
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR）、Value（PER, ROE）、Liquidity（20日平均売買代金等）をDuckDBクエリで計算する関数を実装。
    - データ不足時の None 処理、結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量解析 (`research/feature_exploration.py`)
    - 将来リターン計算 (`calc_forward_returns`)、IC（Spearman）計算 (`calc_ic`)、ランク付けユーティリティ (`rank`)、ファクター統計サマリー (`factor_summary`) を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB SQL で実装。
- DuckDB を使用した内部クエリ実装
  - 各モジュールは DuckDB 接続（DuckDBPyConnection）を受け取り、prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等のテーブルを参照して処理を実行する想定。
- ロギングとフェイルセーフ
  - 各所で INFO/DEBUG/WARNING/ERROR ログを出力し、外部 API エラー時にもフェイルセーフ（ゼロスコアやスキップで継続）となるよう設計。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）および ROLLBACK が失敗した場合の警告ログ処理を実装。
- テスト支援
  - OpenAI 呼び出しのラッパー関数はユニットテストで差し替え可能（unittest.mock.patch を想定）。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Deprecated
- 初版のため該当なし。

### Removed
- 初版のため該当なし。

### Security
- 初版のため特記事項なし。ただし、OpenAI API キーは引数で注入できる設計で、環境変数依存を緩和しています。

---

注記:
- OpenAI 利用箇所（news_nlp, regime_detector）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）の設定を必須とします。未設定時は ValueError を送出します。
- 各モジュールは「ルックアヘッドバイアスを避ける」設計指針を採用しており、処理は target_date に対して過去側のみを参照するようになっています。
- DuckDB のバージョン差異（executemany の空リスト禁止等）に配慮した実装になっています。

今後のリリースでは、ドキュメント追加、テストカバレッジ向上、実稼働（kabu API）連携部分の実装・検証、パフォーマンス改善などを予定しています。