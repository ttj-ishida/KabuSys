# Changelog

すべての注目に値する変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

## [Unreleased]

（未リリース — 現在の開発中の変更点はここに記載します）

## [0.1.0] - 2026-03-31

初回リリース。本リリースは日本株自動売買システム「KabuSys」のコアライブラリを実装します。主にデータ取得・ETL・ファクター計算・ニュースNLP・市場レジーム判定・カレンダー管理・設定管理に関する機能を提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名と __version__ = "0.1.0" を設定。
- 設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機構（プロジェクトルートは .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行の堅牢なパーサ（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
    - Settings クラスでアプリケーション設定をプロパティとして公開（J-Quants トークン、kabu API、Slack、DB パス、監視閾値、環境判定等）。
    - 環境変数検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- AI ニュース解析
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を実装。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたり記事数上限・文字数トリム、JSON Mode を期待したレスポンスのパースとバリデーション。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。非再試行のエラーはスキップして継続（フェイルセーフ）。
    - DuckDB へ冪等的に書き込む処理（DELETE → INSERT、executemany の空リスト回避処理を含む）。
    - calc_news_window: JST ウィンドウの計算ユーティリティ。
- 市場レジーム判定
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（記事が存在する場合のみコール）、API エラー時は macro_sentiment=0.0 でフォールバック。
    - リトライ、エラーハンドリング、JSON パース保護、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK フォールバック）。
    - ルックアヘッドバイアス防止設計（date 引数を明示的に受ける、内部で date.today() を使わない）。
- データプラットフォーム（ETL / パイプライン）
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスの定義（ETL 実行結果の構造化、品質問題・エラーの集約、has_errors / has_quality_errors 等のユーティリティ）。
    - 差分取得・バックフィル方針、品質チェックの扱いに関する設計説明（実装のための基盤）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。
- カレンダー管理
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants からカレンダーデータを差分取得して保存する夜間ジョブ（calendar_update_job）を実装。バックフィル・健全性チェックを実施。
    - market_calendar データがない場合の曜日ベースフォールバック（土日非営業）。
    - DB 値優先だが未登録日は曜日フォールバックで補完する一貫した振る舞い。
- 研究用ユーティリティ（Research）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）およびバリュー（PER, ROE）計算関数を実装。DuckDB 上で SQL とウィンドウ関数を活用して高速に算出。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）算出、ランク化関数（rank）、統計サマリー（factor_summary）を実装。
  - src/kabusys/research/__init__.py で主要関数の公開。
- データモジュール初期構成
  - src/kabusys/data/__init__.py および jquants_client への参照（コード内で使用）。

### Changed
- 設計文書化
  - 各モジュールに詳細なモジュールレベルの docstring を付与し、処理フロー・設計方針・フェイルセーフ挙動を明記。テスト可能性・ルックアヘッドバイアス防止・DuckDB 互換性を意識した実装方針を明示。

### Fixed
- エラーハンドリング強化
  - OpenAI 呼び出しでの各種エラー（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対するリトライやフォールバックを追加。
  - DuckDB への複数行挿入における executemany の空リスト問題に対処（パラメータが空の場合は実行しない）。
  - .env ファイル読み込み失敗時は警告を発し安全に継続。

### Security
- 環境変数の取り扱いに留意
  - Settings._require による必須キーの明示的チェックとエラーメッセージを実装（トークンの暗号化等は別途）。

### Notes / Implementation details
- OpenAI 関連
  - gpt-4o-mini を利用し JSON Mode を期待したレスポンスをパースする設計。レスポンスが不正な場合は安全にスキップして処理を継続する方針。
  - _call_openai_api 関数は各モジュールで独立実装（モジュール間でプライベート関数を共有しないことで結合度を下げ、ユニットテストで差し替えが容易）。
- 日付 / 時刻の扱い
  - ルックアヘッドバイアス防止のため、各関数は datetime.today()/date.today() を参照しない（日付は外部から明示的に受け取る）。
  - ニュース集計ウィンドウは JST 指定で計算し、DB 比較は UTC naive datetime を使用。
- DB 書き込み
  - 多くの書き込み処理は冪等化（DELETE → INSERT、または ON CONFLICT を想定）を意識して実装。
  - トランザクション管理（BEGIN/COMMIT/ROLLBACK）を各所で利用。

### Breaking Changes
- 初回リリースのため該当なし。

### Removed / Deprecated
- 初回リリースのため該当なし。

---

参考: 実装ファイルの概要はコード内の docstring / コメントに基づいて推測して記載しています。必要に応じて各機能の詳細やサンプル利用方法を別途 CHANGELOG の補足やドキュメントに追加してください。