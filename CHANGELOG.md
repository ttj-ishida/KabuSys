CHANGELOG
=========
全ての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから機能・設計・振る舞いを推測して作成した初期の変更履歴です。

[Unreleased]
-----------
- なし（初回リリースは 0.1.0 です）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装
  - 自動 .env 読み込み:
    - プロジェクトルート (.git または pyproject.toml を基準) から .env / .env.local を自動読み込み
    - OS 環境変数を保護する protected 上書き制御、.env.local は override=True による上書き
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応
  - .env 解析機能:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い
    - 不正行のスキップ
  - 必須値チェック (_require) と型／値のバリデーション:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須検証
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 化ユーティリティ

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し OpenAI (gpt-4o-mini) に JSON モードでバッチ投げして銘柄別センチメントを算出
    - タイムウィンドウ定義: target_date に対する前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較
    - バッチ処理: 最大 _BATCH_SIZE（デフォルト20）銘柄ずつ処理
    - 1 銘柄当たりのトークン抑制: _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK によるトリム
    - API 呼び出しの再試行・バックオフ: 429 / 接続断 / タイムアウト / 5xx を指数的バックオフでリトライ
    - レスポンスの頑健なバリデーション: JSON 抽出、"results" の型チェック、コード正規化、数値への変換、±1.0 でクリップ
    - DuckDB への書き込みは冪等（DELETE → INSERT）で部分失敗時に他コードを保護
    - テスト容易性: OpenAI 呼び出しラッパー (_call_openai_api) を patch で差し替え可能
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime を算出
    - マクロニュースは news_nlp.calc_news_window による同一ウィンドウから抽出
    - OpenAI 呼び出し: gpt-4o-mini を JSON モードで利用し、レスポンスを厳密な JSON として期待
    - フェイルセーフ: API やパース失敗時は macro_sentiment=0.0 で継続
    - 冪等な DB 書き込み: BEGIN / DELETE / INSERT / COMMIT（失敗時は ROLLBACK を試行）
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す

- データ基盤関連 (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理ロジックを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB（market_calendar）がない場合は曜日ベース（週末を休場）でフォールバック
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS) により J-Quants からの差分取得 → save_market_calendar を呼出して保存
    - バックフィル機能、健全性チェック（過度に未来の last_date はスキップ）

  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を導入（target_date/取得数/保存数/品質問題/エラーの集約）
    - 差分取得ロジック、バックフィル、品質チェックフレームワークを想定
    - DB 存在チェックや最大日付取得ユーティリティを実装
    - 公開: ETLResult を kabusys.data.etl から再エクスポート

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio
    - バリュー: per, roe（raw_financials の最新レコードを target_date 以前から取得）
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン算出: calc_forward_returns（任意ホライズン、入力バリデーションあり）
    - IC（Information Coefficient）計算: calc_ic（Spearman のランク相関）
    - ランク変換ユーティリティ: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）
    - 外部ライブラリに依存せず標準ライブラリと DuckDB で実装

- モジュール初期化ファイル・エクスポート整理
  - ai.__init__.py で score_news を公開
  - research.__init__.py で主要関数を再エクスポート
  - data.etl は ETLResult を公開

Changed
- （初回）コードベースの設計方針・動作仕様をドキュメント化:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針が明記
  - OpenAI 呼び出しの失敗耐性（ログ警告・フェイルセーフ値）を明確化
  - DuckDB のバージョン依存挙動（executemany の空リスト制約等）への対応

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーの取り扱い:
  - API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を投げて明示的に要求。
  - .env 自動ロード時に OS 環境変数を保護する仕組みを導入（.env の上書きを制限）

Notes / Known issues
- DuckDB への依存:
  - 一部処理は DuckDB のウィンドウ関数や executemany の挙動に依存しており、DuckDB のバージョン差異で動作が変わる可能性がある（コード内に互換対応注釈あり）。
- 未実装 / 除外事項:
  - calc_value では PBR・配当利回り等は現バージョンで未実装。
- 日付/タイムゾーン:
  - ニュースウィンドウ計算は JST に基づく UTC naive datetime を使う設計。タイムゾーンが混入しないよう注意が必要。
- テスト支援:
  - OpenAI 呼び出しの内部ラッパーを patch することで外部 API をモック可能。ただしエンドツーエンドでは DuckDB のテーブル定義やデータが必要。
- 部分書き込みの保護:
  - ai_scores 等のテーブル更新は部分的な失敗に備えて該当コードのみを削除→挿入する方式を採用。全体置換ではないため、運用上の注意点がある。

Author / Contact
- ドキュメントはコードの実装および docstring / コメントから推測して作成しています。実運用や他のブランチに伴う変更は反映されていません。必要であれば、a) 追加のコミット履歴や差分、b) 実際のリリースノート方針を提供ください。