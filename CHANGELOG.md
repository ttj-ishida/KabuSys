# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

※ 本リリースノートはソースコードから推測して作成しています。

## [Unreleased]

（開発中の変更はここに記載します）

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主要なサブパッケージは data / research / ai / monitoring / strategy / execution（公開 API の __all__ に基づく想定）などで構成されています。本バージョンではデータ収集・前処理、研究用ファクター計算、ニュース NLP と市場レジーム判定、マーケットカレンダー管理、ETL パイプライン、環境設定ユーティリティ等の基盤機能を実装しています。

### Added
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env ファイルの自動読み込み機能（プロジェクトルートの探索: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順（OS 環境 > .env.local > .env）。`.env.local` は上書き（override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 行パーサの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート対応とバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無に応じた挙動）
  - protected キーセットによる OS 環境変数保護（上書き回避）。
  - Settings クラスを提供し、主要設定をプロパティで取得:
    - J-Quants, kabu API, Slack, DB パス（DuckDB / SQLite）、環境（development / paper_trading / live）、ログレベル。
  - 環境変数検証（KABUSYS_ENV の有効値、LOG_LEVEL の有効値）と必須変数未設定時の ValueError。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを取得。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 相当の UTC 範囲）を提供する `calc_news_window`。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）とトークン肥大化対策（記事数・文字数上限）。
    - JSON Mode を利用した厳密な JSON レスポンス期待、返却のバリデーションと安全なパース（余分なテキストの復元を含む）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ）。
    - 書き込み処理は部分失敗に備え、スコア取得済みコードのみ DELETE→INSERT（冪等性と既存データ保護）。
    - テスト容易性: OpenAI 呼び出し部（_call_openai_api）を patch で差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - LLM を用いる場合の API キー注入（引数または OPENAI_API_KEY 環境変数）。
    - API 失敗時には macro_sentiment=0.0 を用いるフェイルセーフ実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - news_nlp と内部で `_call_openai_api` を共有しない（モジュール結合の回避、テスト容易性）。

- データ（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を実装。
    - market_calendar テーブルがない場合の曜日ベースフォールバック（週末除外）を提供。
    - DB 登録値優先かつ未登録日は一貫した曜日フォールバックを行う設計。
    - calendar_update_job: J-Quants から差分取得し market_calendar を冪等的に保存する夜間ジョブ（バックフィル、健全性チェック含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー等を含む）。
    - 差分更新、バックフィル、品質チェックの設計を反映。
    - jquants_client 経由での保存処理を想定。
    - etl モジュールは ETLResult を公開。

- 研究用（src/kabusys/research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を算出（最新財務データを target_date 以前で検索）。
    - DuckDB の SQL を活用し、外部 API への依存なしで実装。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算（rank 関数と組み合わせ）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 計算。
    - rank: 同順位は平均ランクで処理するランキング関数。
    - 外部依存なし（pandas 等不使用）。

- リサーチパッケージの公開インターフェースを整理（src/kabusys/research/__init__.py）。

### Changed
- （初回リリースのため過去の変更はなし。設計上の重要方針・注意点を明示）
  - 主要設計方針（全体的な注意点）:
    - ルックアヘッドバイアス防止のため、date.today() / datetime.today() を関数内部で参照しない（すべて target_date を明示的に渡す）。
    - DuckDB のバージョン差異（例えば executemany に空リストが渡せない等）を考慮した実装。
    - API 呼び出しは失敗に対してフェイルセーフに振る舞い（LLM 失敗時のスコア 0.0 や対象銘柄のスキップ）し、例外の伝播は DB 書き込み等の致命処理に限定。

### Fixed
- （初回リリースのため「修正」は該当なし。ただしコード内にログや回復処理を多数実装）

### Security
- 設定・トークン管理:
  - OpenAI API キー、J-Quants トークン、Slack トークン等は環境変数から取得する設計。必須項目が unset の場合は ValueError を返すため、誤設定に気づきやすい。
  - .env の読み込みはデフォルトで有効（テスト時に無効化可能）。
  - OS 環境変数は protected として .env による上書きを保護。

### Known limitations / Notes
- OpenAI（LLM）依存:
  - gpt-4o-mini を前提に設計しているため、利用には有効な OpenAI API キーが必要。
  - LLM レスポンスが JSON 形式でない場合やフォーマットが崩れている場合はスキップされるか、フェイルセーフ値（0.0）にフォールバックする。
- DuckDB のバインド挙動（リストバインド/ executemany の空リスト制約）に注意が必要。
- news_nlp / regime_detector の内部 OpenAI 呼び出しはモジュールごとに独自関数を持つため、テストでの差し替えは各モジュール内の _call_openai_api を patch する必要がある。
- データの完全性・品質チェックは ETL 内に実装点があるが、運用ポリシーによっては追加のルールが必要。

---

完全な API 仕様や運用手順、導入手順については各モジュールのドキュメント（コード中の docstring や参照する Design/Platform ドキュメント）を参照してください。