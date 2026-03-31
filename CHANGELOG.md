# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31
初回リリース（ベースライン機能の実装）。

### Added
- パッケージのメタ情報を追加
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開用 __all__ の定義（data, strategy, execution, monitoring）

- 環境変数 / 設定管理モジュール（kabusys.config）
  - .env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - 複雑な .env 行のパース対応（export プレフィックス、クォート内エスケープ、インラインコメントの扱い）
  - override / protected オプション対応の .env 読み込み
  - Settings クラス: 必須変数の取得（_require）と各種設定プロパティ
    - JQUANTS / kabu / Slack / DB パス等のプロパティ
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティ（is_live / is_paper / is_dev）

- AI 関連モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約
    - OpenAI (gpt-4o-mini) の JSON mode を用いてバッチでセンチメント評価
    - チャンク処理（最大 20 銘柄/回）・1 銘柄当たりトリム（記事数・文字数上限）
    - リトライ/バックオフ戦略（429, ネットワーク断, タイムアウト, 5xx）
    - レスポンスバリデーション（JSON 抽出、results フォーマット、既知コードのみ採用）
    - スコアは ±1.0 にクリップ
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）
    - 公開 API: score_news(conn, target_date, api_key=None)
    - calc_news_window(target_date) によるニュース収集ウィンドウ計算（JST 基準）

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - マクロニュース抽出（キーワードでフィルタ、最大記事数制限）
    - OpenAI 呼び出しラッパーとリトライ処理（エラー種別に応じた再試行）
    - レジームスコア合成・クリッピング・ラベリング（bull/neutral/bear）
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - 公開 API: score_regime(conn, target_date, api_key=None)

  - news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出し実装を持ち、
    テスト時に差し替え可能な設計（private な呼び出し関数をモジュール間で共有しない）

- Research モジュール（kabusys.research）
  - factor_research（モメンタム / ボラティリティ / バリュー）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR（平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算（最新レポートを利用）
    - 関数は DuckDB を用いた SQL + Python 実装、prices_daily / raw_financials のみ参照
  - feature_exploration（将来リターン / IC / 統計）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマンランク相関（ランク化は平均ランク、ties に対応）
    - rank: 同順位は平均ランクに変換（丸め処理で浮動小数の誤差を吸収）
    - factor_summary: count/mean/std/min/max/median の統計要約
  - research パッケージはデータ処理・解析用ユーティリティを提供（本番取引 API にはアクセスしない）

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理・営業日判定機能
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - カレンダーデータがない場合は曜日ベース（週末を休日）でフォールバック
    - 最大探索制限 (_MAX_SEARCH_DAYS) による無限ループ防止
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新
      - バックフィル（直近 _BACKFILL_DAYS 分の再取得）・健全性チェック実装
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）
    - ETL パイプラインの基礎（差分取得、保存、品質チェックに対応する設計）
    - _get_max_date / _table_exists 等のユーティリティ実装
    - ETLResult は品質検査結果やエラー情報を保持し、to_dict() でシリアライズ可能

- 共通設計上の重要な方針・安全策を実装
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照しない設計（関数は target_date を受け取る）
  - OpenAI / 外部 API の失敗に対するフォールバック（例: macro_sentiment=0.0、スコア未取得時はスキップ）
  - DB 書き込みは冪等化（DELETE → INSERT、トランザクション、ROLLBACK の保護ログ）
  - DuckDB のバージョン挙動への互換性考慮（executemany の空パラメータ回避など）
  - テスト容易性: OpenAI 呼び出しの差し替え、環境自動読み込みの無効化フラグ等

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

### Notes / 補足
- OpenAI を使う機能（news_nlp, regime_detector）は API キーを api_key 引数で注入可能。引数未指定時は環境変数 OPENAI_API_KEY を参照。
- .env のパースは POSIX シェル風の挙動（export, クォート、エスケープ、コメント）に広く対応するが、完全なシェルパーサとは異なるため極端に複雑な行は期待通りに解釈されない可能性があります。
- DuckDB を前提とした SQL 実装であり、各関数は指定されたテーブル（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）が存在することを前提に動作します。

-----------
今後のリリースでは、以下のような改善を予定しています（予定項目）:
- strategy / execution / monitoring 周りの実装とインテグレーション
- ユニットテスト拡充・CI の整備
- スケーリング（並列化、API コール最適化）やコスト削減（モデル選択）の検討
- セキュリティ監査と Secrets 管理の強化

（以上）