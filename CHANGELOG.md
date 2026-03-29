Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに沿って変更履歴を管理します。

フォーマット
- バージョン番号（リリース日）
- セクション: Added / Changed / Fixed / Security

Unreleased
---------

（現時点の未リリース変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を公開。
- パッケージ構成を提供:
  - パブリックモジュール: data, research, ai, monitoring, strategy, execution 等の名前空間を __all__ で公開。

- 環境設定 (.env) の自動/堅牢な読み込み (kabusys.config)
  - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応するパーサ実装。
  - OS 環境変数を保護するため protected キーセットを導入し、.env.local による上書き挙動を制御。
  - 必須環境変数未設定時に ValueError を送出する _require()、有効値検証（KABUSYS_ENV / LOG_LEVEL）を備えた Settings クラスを提供。
  - デフォルトの DB パス（duckdb/sqlite）や kabu API の base URL 等のプロパティを実装。

- AI ニュース解析とレジーム判定 (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
    - バッチサイズ、文字数制限、記事数制限、JSON Mode を利用した出力バリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ、部分失敗時に他銘柄の既存スコアを保護するデータ書き込みロジック（DELETE→INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
    - lookahead バイアス回避のため datetime.today() を参照しない設計。ニュース収集ウィンドウ算出（calc_news_window）を実装。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - prices_daily / raw_news / market_regime を使用し、DB へ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しの失敗やパース失敗は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - OpenAI 呼び出し関数はモジュール間結合を避け別実装とし、テスト差し替えを想定。

- データプラットフォーム: カレンダー管理・ETL (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。

  - pipeline / ETL:
    - ETLResult データクラスを導入し、ETL 実行結果（取得件数・保存件数・品質チェック・エラー等）を集約。
    - 差分更新、バックフィル、品質チェック設計に基づく ETL ユーティリティを実装。DB 最大日取得やテーブル存在チェック等のユーティリティを提供。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足時の扱いを定義。
    - calc_volatility: 20 日 ATR / 相対 ATR / 20 日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - すべて DuckDB と SQL で完結、実行時に本番口座や発注 API へアクセスしない設計。

  - feature_exploration:
    - calc_forward_returns: 指定 horizon の将来リターンを LEAD を使って一括計算（ホライズンバリデーションあり）。
    - calc_ic: スピアマンのランク相関による IC を実装（同順位は平均ランク処理）。
    - factor_summary / rank: 基本統計量やランク変換ユーティリティを提供。
    - 外部依存 (pandas 等) を使わない純粋 Python 実装。

- ロギング・デバッグ・テスト支援
  - 各所で詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - OpenAI 呼び出しを patch してテスト時に差し替え可能にするフックを設置。

Changed
- （初回リリースのため過去バージョンからの変更はなし。ただし設計上の注意点を COALESCE 等の扱いで明示）
  - DuckDB のバージョン差異（executemany の空リスト制約）を考慮した安全な実装を採用。
  - API エラー処理で status_code の有無に応じた安全な判定を実装（将来の SDK 変更に耐性）。

Fixed
- 初回リリースにつき過去バグ修正履歴はなし。  
  ただし多くのフェイルセーフ（APIパース失敗フォールバック、DB ROLLBACK ハンドリング、健全性チェック等）を実装して既知の失敗ケースに対処。

Security
- このリリースで公表された特定のセキュリティ修正はありません。  
- 注意: OpenAI API キー等の機密情報は環境変数経由で設定することを想定しています（Settings._require により必須キーの未設定を検出）。

Notes / 設計上の重要なポイント
- ルックアヘッドバイアス回避: AI/リサーチモジュールは datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を明示的に渡す設計。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 相当）にして部分失敗で既存データを不意に消さない設計。
- リトライ/バックオフ: OpenAI 等の外部 API 呼び出しは指数バックオフと限定的なリトライを実装（5xx やネットワーク断を対象）。
- JSON レスポンス耐性: LLM レスポンスは余計な前後テキストが混ざることを想定し、波括弧抽出などで復元を試みる実装を含む。
- テスト容易性: _call_openai_api の差し替え、環境変数自動ロードの無効化フラグによりユニットテストを行いやすくしている。

開発者向け
- パッケージのバージョンは src/kabusys/__init__.py の __version__ にて管理。
- 環境依存の自動ロードが不要なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の TODO（抜粋）
- PBR・配当利回りなどのバリューファクター拡張。
- モデルの切り替えやプロンプト改善による LLM 評価品質向上。
- モジュール間のさらに明確なインターフェース設計（例: ai と research の共通ユーティリティ）。

-- END --