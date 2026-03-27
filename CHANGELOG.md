# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys` を実装し、サブパッケージ（data, research, ai, ...）を公開。
  - バージョン情報 `__version__ = "0.1.0"` を追加。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（CWD非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサーは以下をサポート/対処:
    - `export KEY=val` 形式、シングル／ダブルクォートとバックスラッシュエスケープ、インラインコメントの扱い（空白直前の `#` をコメントと認識）。
    - ファイル読み込み失敗時のワーニング出力。
    - OS 環境変数を保護するための protected キーセット（上書き防止）。
  - 設定アクセサ `Settings` を提供（J-Quants、kabu API、Slack、DB パス、環境モード、ログレベルなど）。
    - 環境変数未設定時は明示的なエラーを投げる必須項目アクセサ（_require 関数）。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値セットを定義）。
    - パスは Path オブジェクトとして返却（expanduser を適用）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）算出ユーティリティ `calc_news_window` を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数トリム（上限設定）を実装。
    - 再試行ロジック（429・接続断・タイムアウト・5xx に対する指数バックオフ）、レスポンスの厳格なバリデーション（JSON 抽出、results 配列検証、コード照合、数値検査）。
    - スコアの ±1.0 クリップ、取得成功銘柄のみを対象に ai_scores テーブルへ冪等的に置換（DELETE→INSERT）。
    - テスト容易性: OpenAI 呼び出し関数はモック差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは gpt-4o-mini、JSON レスポンスをパースして macro_sentiment を取得。
    - API 障害時は macro_sentiment=0.0 にフォールバックして処理を継続するフェイルセーフを実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - lookahead バイアス回避のため、内部処理は datetime.today()/date.today() に依存しない（target_date 引数で完全指定）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを前提に市場カレンダー（market_calendar）を管理する API を提供。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 夜間バッチ `calendar_update_job` で J-Quants から差分取得→保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表す `ETLResult` dataclass を公開（to_dict で品質問題を整形して返却）。
    - 差分取得、バックフィル、品質チェック（quality モジュール経由）の設計方針を実装。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。
    - DuckDB executemany の空リスト制約への対処（空時は実行しない）を実装。
  - jquants_client 用ユーティリティの公開（etl から ETLResult を再エクスポート）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数群を実装。
    - 欠損・データ不足時の None 扱い、結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（複数ホライズン対応、ホライズン入力検証）、IC（Spearmanのρ）計算、ランク変換、ファクター統計要約（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリ／DuckDB で完結。

- テスト性 / 安全設計
  - LLM 呼び出し箇所はテストで差し替え可能（関数単位で patch する設計）。
  - ルックアヘッドバイアス回避を明示的に設計（関数は全て target_date を受け日時依存を避ける）。
  - DB 書き込みは冪等を意識（DELETE→INSERT のパターンなど）している。

### Fixed / Defensive
- API 応答・ネットワーク問題に対する回復性を強化
  - OpenAI 呼び出しでの RateLimit/接続/タイムアウト/5xx に対して指数バックオフで再試行。最終的に失敗した場合は警告ログを出し安全側の既定値（0.0）で継続する。
  - JSON モードでも前後余計なテキストが混入することを想定して、最外の { ... } を抽出してパースする耐性を実装。
  - レスポンスバリデーションで未知銘柄コードや非数値スコアを無視することで部分失敗時の影響を最小化。

- DuckDB 関連の互換性対策
  - executemany に空リストを渡すとエラーになる点に対処（空のときは SQL 実行をスキップ）。
  - DuckDB が返す日付値を date オブジェクトに正しく変換するユーティリティを追加。

### Security
- 環境変数に API キー等の機密情報を要求（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。未設定時は明確な例外を返すことで起動時の誤設定を検出しやすくしている。

### Notes / Design decisions
- 多くの処理は「DB の過去データのみ参照し target_date を明示的に受け取る」ことでルックアヘッドバイアスを完全に排除する設計を採用。
- AI モジュールは gpt-4o-mini をデフォルトで使用し、JSON Mode を活用して機械判定の整合性を高める実装になっている。
- 一部公開 API は整数ではなく明示的な返り値（例: score_news は書き込んだ銘柄数を返す、score_regime は成功コード 1 を返す）を採用している。

---

（本 CHANGELOG は、ソースコードの内容から機能・挙動を推測して作成しています。実際のリリースノート作成の際は実績・変更履歴と照合のうえ必要に応じて修正してください。）