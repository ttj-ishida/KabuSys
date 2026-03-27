# Changelog

すべての変更は Keep a Changelog の思想に準拠しています。  
このファイルはリポジトリ内のコード内容から推測して作成した CHANGELOG.md です。

なお、日付はリリースの仮定日として記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を提供します。主要なサブモジュールはデータ ETL・マーケットカレンダー管理、リサーチ（ファクター計算・特徴量探索）、AI ベースのニュース NLP / 市場レジーム判定、環境設定ユーティリティなどです。

### Added
- パッケージ基礎
  - パッケージバージョン `__version__ = "0.1.0"` の設定。
  - パッケージの公開インターフェース（data, strategy, execution, monitoring）の定義。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
    - プロジェクトルートの検出は __file__ ベースで親ディレクトリに .git または pyproject.toml を探索して行う（CWD 非依存）。
  - 高度な .env パーサーを実装:
    - `export KEY=val` の形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなしの値でのインラインコメント（`#`）処理は直前が空白またはタブの場合のみコメント扱い。
    - ファイル読み込み失敗時は警告を出力して継続。
  - Settings クラスを提供し、必須・任意設定値をプロパティで取得可能:
    - J-Quants / kabuステーション / Slack / DB パス等の主要設定項目。
    - `env` と `log_level` のバリデーション（許容値チェック）。
    - `is_live` / `is_paper` / `is_dev` の便宜プロパティ。

- データ / ETL（kabusys.data.pipeline / etl）
  - ETL 実行結果を表す `ETLResult` データクラスを公開（to_dict により品質問題を辞書化可能）。
  - ETL パイプライン設計:
    - 差分更新・バックフィル（既存データの再取得）・品質チェック（quality モジュールとの連携）を想定した実装方針。
    - 最小データ開始日、カレンダー先読み、デフォルトバックフィル日数等の定数を定義。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダー管理 API 用ユーティリティ:
    - market_calendar テーブルの有無やデータ状態チェック。
    - 営業日判定 API:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録が無い日については曜日ベースのフォールバック（週末を非営業日）。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 探索の最大範囲制限（_MAX_SEARCH_DAYS）やバックフィル期間等の安全策を導入。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None 戻し。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。必要データ未満は None。
    - calc_value: raw_financials から直近財務データを取得し PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB を用いた高速 SQL ベース実装。外部 API や発注処理には依存せず安全に計算可能。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons 引数の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。3 銘柄未満なら None を返す。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めによる ties 対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - すべて標準ライブラリと DuckDB のみで実装（pandas 等に未依存）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON mode でバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用（UTC naive datetime）。
    - バッチ処理と制限:
      - 1 API 呼び出しで最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたり最大記事数 10 件、最大文字数 3000 字にトリム。
    - 再試行ロジック:
      - 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ（最大 _MAX_RETRIES）。
      - それ以外のエラーやパース失敗は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証:
      - JSON パース（前後余計テキストの切り出し復元含む）、"results" リスト、各要素の code/score 検証、未知コードの無視、スコアの数値化と有限性チェック、±1.0 にクリップ。
    - DuckDB の executemany の仕様考慮（空リストを渡さないガード）を実装。
    - テスト用に _call_openai_api の差し替え（patch）を想定。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書込。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースは news_nlp.calc_news_window を用いて記事ウィンドウを取得し、OpenAI（gpt-4o-mini）で JSON 出力を期待。記事がない場合は macro_sentiment=0.0 として継続。
    - 再試行ロジックとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - 設定可能な閾値・重み・モデル名などはモジュール定数として明示。

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Security
- OpenAI API キーは引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照。直接コード内に埋め込まない設計。

### Notes / Design decisions（重要な設計上の注意）
- ルックアヘッドバイアス対策:
  - AI モジュール・リサーチ関数は内部で datetime.today() / date.today() を参照しない（target_date を明示受け渡し）。これによりバックテストの正当性を保つ。
- 冪等性と部分失敗保護:
  - DB 書き込みは基本的に DELETE → INSERT の置換操作で実装し、部分失敗時に既存データを不必要に消さないよう配慮。
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン対策など、DuckDB の実装差異を考慮した実装。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数（_call_openai_api）経由で実装され、unittest.mock.patch による差し替えを想定。
- フォールバック挙動:
  - カレンダーデータ未取得時は曜日ベース（週末除外）で営業日判定を行うなど、外部データ未整備時の安全なフォールバックを採用。
- ログ・ワーニング:
  - データ不足や API エラー時は例外を投げずに警告ログを出す設計箇所があるため、運用時はログ監視が重要。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートは開発者による確認・追記を推奨します。）