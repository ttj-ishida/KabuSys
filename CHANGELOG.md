CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
主要バージョンはパッケージの __version__（0.1.0）に合わせています。

フォーマットの簡単な説明:
- Added: 新規追加機能
- Changed: 既存の変更（互換性に影響が少ない変更）
- Fixed: バグ修正
- Security: セキュリティに関する修正や注意点

[Unreleased]
------------

（現時点では未リリースの差分はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージルート: kabusys（__init__.py に __version__ = "0.1.0"）
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=True）
  - OS 側の既存環境変数を保護する protected 機構を追加（上書き禁止）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - .env の行パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス等の設定をプロパティで取得）
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と便利なプロパティ（is_live / is_paper / is_dev）を追加

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）の JSON モードで銘柄別センチメント（-1.0〜1.0）を取得
    - バッチ処理（最大 20 コード/チャンク）、記事数・文字数制限（記事数上限、1 銘柄当たり最大文字数トリム）を実装
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフのリトライ実装
    - レスポンス検証（JSON パース、results 配列・code・score の検証）とスコアのクリップ
    - DuckDB 互換性考慮: executemany に空リストを渡さない実装、部分失敗時に既存スコアを保護する DELETE→INSERT ロジック
    - テスト容易性のため _call_openai_api を差し替え可能
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換して扱う）

  - regime_detector.score_regime
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - マクロキーワードによる raw_news のフィルタリング、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価（記事がなければ LLM 呼び出し無し）
    - API エラー時は macro_sentiment = 0.0 でフェイルセーフ継続
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK 復旧処理
    - テスト容易性のため _call_openai_api を差し替え可能

- Research（研究用）機能（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を DuckDB の prices_daily を用いて計算
    - calc_volatility: 20日 ATR（atr_20）, 相対 ATR（atr_pct）, 20日平均売買代金, 出来高比率を計算
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS=0/欠損時は None）
    - データ不足時の None 扱い、営業日ベース（連続レコード）でのホライズン設計、DuckDB SQL と Python の組合せで効率的に計算

  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装（None/非有限値を除外、有効レコード < 3 は None）
    - rank: 平均ランク（同順位の平均順位）実装（丸めにより ties の安定化）
    - factor_summary: 各ファクター列に対する count/mean/std/min/max/median を計算
    - pandas 等に依存せず標準ライブラリのみで完結

- Data（データパイプライン）機能（kabusys.data）
  - calendar_management
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が存在しない場合は曜日（平日）ベースのフォールバックを使用
    - DB の登録値優先、未登録日は曜日フォールバックで一貫した判定ロジック
    - calendar_update_job: J-Quants API からカレンダーを差分取得し保存（バックフィルと健全性チェックを実装）
    - 最大探索日数やバックフィル日数、先読み日数などの安全パラメータを導入

  - pipeline / etl
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラー一覧を格納）
    - ETL の差分更新方針、バックフィルのデフォルト、品質チェックの扱い（致命的エラーがあっても処理継続して結果を返す設計）を明記
    - DuckDB 互換性（テーブル存在チェック・最大日付取得ユーティリティ等）を実装

  - etl モジュールで ETLResult をエクスポート（公開インターフェース）

Changed
- 多くのモジュールで「ルックアヘッドバイアス防止」の方針を採用
  - datetime.today() / date.today() を内部参照せず、全ての処理は target_date を明示的に受け取る設計に統一
  - これによりテスト容易性と再現性が向上

- DuckDB 互換性対応
  - executemany に空リストを渡すと失敗するバージョンに配慮した実装（空チェックの追加）
  - 日付型の取り扱いで安全に date オブジェクトへ変換するヘルパーを追加

Fixed
- OpenAI / API 呼び出し関連の堅牢性向上
  - 429 / ネットワーク断 / タイムアウト / 5xx に対するリトライ戦略を導入
  - API エラーや JSON パース失敗時にプロセス全体が停止しないようにフォールバック（0.0 スコアや空スコア辞書）を採用
  - APIError の status_code がない場合でも安全にリトライ判定する処理を追加

- DB 書き込みの冪等性とエラー復旧
  - market_regime / ai_scores の書き込みで BEGIN/DELETE/INSERT/COMMIT パターンと ROLLBACK 捕捉を実装
  - 部分失敗時に他の既存データを不必要に削除しない設計（書き込み対象コードを限定）

Security
- 環境変数ロード時に OS 環境を保護する設計を採用（.env による意図しない上書きを防止）
- OpenAI API キー未設定時は明示的な ValueError を投げ、誤った動作を未然に防止

Notes / Design Decisions
- 各種外部 API 呼び出し（OpenAI、J-Quants）は失敗しても「完全停止」させないフェイルセーフ設計（可能な限り処理を継続して結果を返す）
- テストしやすさを重視して、API 呼び出しラッパー（_call_openai_api 等）は unittest.mock で差し替え可能に実装
- 外部依存（pandas 等）を避け、標準ライブラリと DuckDB SQL を中心に実装して移植性と軽量性を確保

Deprecated
- なし

Removed
- なし

--- 

補足:
- 上記はコードベースの内容から推測した CHANGELOG です。実際のリリースノートでは更に利用上の注意（依存パッケージのバージョン、DB スキーマ期待値、環境変数の具体例など）を付けることを推奨します。