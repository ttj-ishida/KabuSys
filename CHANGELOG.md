Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- (なし)

0.1.0 - 2026-04-02
------------------

Added
- 初回公開 (kabusys 0.1.0)
  - パッケージ構成の追加
    - kabusys パッケージの公開 API（data, strategy, execution, monitoring）を定義。
    - バージョン情報: __version__ = "0.1.0"。

  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルおよび環境変数からの設定読み込みを実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動的にルートを探索（cwd に依存しない挙動）。
    - .env 自動読み込みの優先度: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサを実装:
      - export KEY=val 形式に対応。
      - シングル／ダブルクォートのエスケープ処理を適切に扱う。
      - コメント処理（クォートなしの '#' は直前が空白／タブのときのみコメントとして扱う）を実装。
      - ファイル読み込み失敗時は警告を発行して継続。
    - 設定項目（プロパティ）を提供:
      - J-Quants、kabuステーション、Slack、データベースパス（DuckDB/SQLite）、監視閾値（CPU/メモリ/ディスク）、PID ファイルパス、実行環境（development/paper_trading/live）、ログレベル。
    - 必須変数取得ヘルパー _require を追加（未設定時は ValueError）。

  - AI / ニュース NLP (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (gpt-4o-mini) に対して JSON Mode でバッチ評価を実行して ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（JST 基準）を明確化:
      - 前日 15:00 JST ～ 当日 08:30 JST（DB 比較は UTC naive datetime）。
    - バッチ処理:
      - 1 コールあたり最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - API エラー処理:
      - 429（レート制限）・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。
      - それ以外のエラーはスキップし、処理を継続（フェイルセーフ）。
      - レスポンスのバリデーションを厳格に実行し、想定外のレスポンスはそのチャンクをスキップ。
    - 結果は ±1.0 にクリップして保存。部分失敗時は影響範囲を限定（該当 code のみ DELETE → INSERT）して既存データを保護。

  - AI / 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込み。
    - マクロセンチメントはニュースタイトルのサブセット（マクロキーワード）を LLM で評価。記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0 を採用。
    - LLM 呼び出しは retry / backoff を行い、API 失敗時は安全側の値（0.0）にフォールバック。JSON レスポンスのパース失敗時もフォールバック。
    - データ読み込み（prices_daily）ではルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の形で冪等化。失敗時は ROLLBACK を試みて例外を伝播。

  - データプラットフォーム関連 (kabusys.data)
    - calendar_management:
      - JPX カレンダー管理（market_calendar テーブル）と営業日ロジックを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB 未取得時は曜日ベース（土日非営業）でフォールバック。DB が一部しかない場合でも一貫した挙動を維持。
      - calendar_update_job を実装: J-Quants クライアント経由で差分取得し冪等保存、バックフィルと健全性チェックを実施。
    - pipeline / etl:
      - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラーなどを含む）。
      - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールと連携）。
    - その他ユーティリティ:
      - テーブル存在チェック、最大日付取得等のヘルパーを提供。

  - リサーチ / ファクター解析 (kabusys.research)
    - factor_research:
      - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER/ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比）を DuckDB SQL を用いて計算する関数を提供（calc_momentum, calc_value, calc_volatility）。
      - データ不足時の None 扱い、ルックアヘッド防止のため target_date 未満のみ参照する等の設計方針を遵守。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランクは同順位平均ランクで算出）。
      - 統計サマリー（factor_summary）と rank ユーティリティを提供。
    - すべての計算は prices_daily / raw_financials のみ参照し、本番発注 API 等にはアクセスしない設計。

  - 汎用設計方針・品質改善
    - ルックアヘッドバイアスを避けるため、すべてのアルゴリズムで datetime.today()/date.today() を直接参照しない設計を採用（ターゲット日を明示的に渡す）。
    - DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT 形を想定）して部分失敗時のダメージを限定。
    - OpenAI 呼び出し周りはリトライ・パース失敗時の安全側フォールバックやログ出力を実装。
    - テスト用の差し替えポイント（_call_openai_api のパッチ等）を用意してユニットテストを容易に。

Fixed
- 初版につき該当なし。

Changed
- 初版につき該当なし。

Removed
- 初版につき該当なし。

Security
- API キーの取り扱い:
  - OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で注入。未設定時は ValueError を送出して明示的に失敗させる設計。
  - .env 自動読み込みでは既存の OS 環境変数を保護するため保護セットを利用（上書き回避）。

Notes
- J-Quants クライアント（jquants_client）や quality モジュール等の外部連携先は本コードの参照先として想定されており、実運用ではそれらの実装・設定が必要です。
- DuckDB との互換性や executemany の挙動（空リスト禁止など）に配慮した実装を行っています。