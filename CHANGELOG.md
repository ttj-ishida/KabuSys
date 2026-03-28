# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。  
初期バージョンの機能追加・設計方針・既知の挙動などをこのファイルで説明します。

なお、バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]

（今後の変更をここに記載）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な目的はデータ取得・ETL・カレンダ管理・リサーチ（ファクター計算）・ニュース/レジームの AI 評価までを含む基盤機能を DuckDB と OpenAI を用いて実装することです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - モジュール構成: data, research, ai, execution, strategy, monitoring（__all__ を通じて公開）。

- 設定 / 環境変数管理（kabusys.config）
  - .env 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env/.env.local の読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理（クォートがない場合の '#' を一部コメントとして扱う）に対応。
  - Settings クラスを提供し、主要環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live を検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news + news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメント（-1.0〜1.0）を評価し ai_scores テーブルへ書き込む機能。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたり記事上限および文字数トリムを実装。
    - JSON Mode を利用し、レスポンス検証・スコアのクリップ（±1.0）・部分成功時は該当コードのみ置換する安全な DB 書き込み（DELETE → INSERT）を行う。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をモック可能に設計。
    - calc_news_window: JST ベースのニュース集計ウィンドウ計算ユーティリティを提供（前日15:00〜当日08:30 JST）。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp ベースのマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼出しは独立実装でモジュール間の結合を低減。
    - MA のデータ不足や API 失敗時は安全側（中立判定や macro_sentiment=0.0）で継続。
    - リトライ・エラーハンドリングを実装（RateLimit/Connection/Timeout/5xx の扱いを明確化）。

- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar を用いた JPX カレンダー操作と判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（週末は非営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を逐次更新する夜間バッチ処理（バックフィル・健全性チェックを実装）。
  - pipeline / ETL
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーログを保持）。
    - ETL パイプライン設計に関するユーティリティ（最終取得日の検査、差分取得、バックフィルの方針、品質チェックとの連携方針など）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB 上で SQL + Python により完結（外部 API にアクセスしない設計）。
  - feature_exploration
    - calc_forward_returns: 将来リターン（指定営業日ホライズン）を効率的に取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランキング・統計サマリーユーティリティを提供。
    - pandas 等への依存なしに標準ライブラリで実装。

- テスト/運用支援
  - OpenAI 呼び出し部分はモック可能な設計（ユニットテストで差し替え容易）。
  - DuckDB のバージョン差（executemany の空リスト問題など）を回避するためのガード実装。

### Changed
- 初回リリースのため該当なし（新規追加のみ）。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 該当なし。

### Security
- OpenAI API キーや各種トークンは環境変数経由で取得する設計。コード内に固定の API キーを埋め込まないでください。
- .env 自動読み込みはテスト目的で KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

### Migration notes / 運用メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を利用するには OPENAI_API_KEY が必要（score_news, score_regime の引数で上書き可）。
- デフォルト DB パス: DUCKDB_PATH= data/kabusys.duckdb（必要に応じて変更）。
- .env のフォーマット: export キーワード・シングル/ダブルクォート・エスケープ・コメント等の扱いに対応していますが、複雑なケースは事前確認を推奨します。
- DuckDB に対する executemany 等の操作はバージョン依存の挙動を考慮した実装になっていますが、運用 DB のバージョン互換性は確認してください。
- calendar_update_job は J-Quants クライアント実装（kabusys.data.jquants_client）に依存します。API 呼び出し時の例外はログ出力のうえ 0 を返すフェイルセーフ。

### Known issues / 既知の制約
- News / Regime の LLM 呼び出しは gpt-4o-mini を想定しており、API のレスポンスフォーマットや RateLimit によってはスコアが取得できない場合があります。その場合はフェイルセーフとしてスコア計算を継続（0.0 やスキップ）します。
- calc_momentum の ma200_dev は対象銘柄の直近 200 行未満では None を返す（データ不足）。
- カレンダーデータがまばらな場合、DB 登録日は優先するが未登録日は曜日フォールバックで補完するため、完全なカレンダーデータがないと一部の判定が曜日ベースとなることに注意してください。
- DuckDB 0.10 系での executemany の仕様（空リスト不可）を回避するためのガードが入っていますが、将来の DuckDB バージョンではこれらのコードの簡素化が可能です。

---

貢献・バグ報告・改善提案は Issue/PR を通じて歓迎します。