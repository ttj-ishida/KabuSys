CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。
初版リリース: 0.1.0

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回リリース: kabusys 0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py によりバージョン "0.1.0" を公開。パッケージの公開 API として data, strategy, execution, monitoring を __all__ で指定。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード:
    - プロジェクトルートを .git または pyproject.toml を基準に特定して .env, .env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env.local は .env を上書き（override）する挙動。
    - OS 環境変数は保護（protected）され、上書きされない。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視、export KEY=val 形式の対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - クォート無しの場合のインラインコメント検出（直前がスペース/タブの場合）
  - 必須環境変数取得用の _require()、各種プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
    - KABUSYS_ENV（development/paper_trading/live）の検証
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証
    - DBパス設定（DUCKDB_PATH / SQLITE_PATH）等
  - Settings インスタンスを settings として公開。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py
    - JPX マーケットカレンダー管理機能を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - market_calendar テーブルがある場合は DB の値を優先、未登録日は曜日ベースのフォールバック（週末除外）。
      - next/prev/get は最大探索日数を設けて無限ループを防止。
      - calendar_update_job: J-Quants から差分取得して冪等的に保存（fetch + save）、バックフィルや健全性チェックを実装。
      - DuckDBとのやり取りにおける日付型変換ユーティリティを提供。
  - pipeline.py / etl.py
    - ETL パイプライン用の共通インターフェースと実装方針を追加。
    - ETLResult dataclass を実装（ETL 結果集計、品質問題 list、エラー list、has_errors / has_quality_errors / to_dict 等を備える）。
    - 差分更新、バックフィル、品質チェックの設計方針（品質問題の収集は続行、呼出元で判断）を反映。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - etl は pipeline.ETLResult を再エクスポート。

  - 実装ノート:
    - DuckDB 互換性考慮: executemany に空リストを渡せないバージョン対策を実装。
    - date 型の扱いを統一して timezone 混入を防止。

- 研究（Research）モジュール（src/kabusys/research/*）
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）等。データ不足時は None を返す。
      - calc_volatility: atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio 等。必要期間に満たない場合は None を扱う。
      - calc_value: raw_financials から最新報告を取り出し PER / ROE を計算（EPS が 0 か欠損時の扱いを考慮）。PBR・配当利回りは未実装。
    - DuckDB ベースの SQL + Python アプローチで実装し、本番売買APIへアクセスしない設計。
    - ログ出力による処理状況通知を実装。
  - feature_exploration.py
    - 研究向けユーティリティを実装:
      - calc_forward_returns: 指定 horizon（営業日数）での将来リターンを一括取得可能。horizons の検証（正の整数、<=252）あり。
      - calc_ic: Spearman ランク相関（Information Coefficient）計算。NULL や ties を適切に扱い、有効レコード数が少ない場合は None を返す。
      - rank: 同順位は平均ランクとして処理。小数丸め（round 12 桁）で ties の漏れを防止。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - pandas 等の外部依存を持たない純粋標準ライブラリ実装。

  - research パッケージの公開 API を整理（__all__）して利用しやすくした。

- AI / NLP（src/kabusys/ai/*）
  - news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄毎のセンチメントスコアを算出。
    - calc_news_window により JST 基準で前日 15:00 ～ 当日 08:30（UTC に変換して扱う）を対象ウィンドウとして正確に計算。
    - 銘柄ごとに最大記事数・最大文字数トリムを実施（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - バッチ処理（最大 _BATCH_SIZE 銘柄 / API コール）およびチャンク単位でのリトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション（JSONパース、results 配列の検証、code の正規化、score の数値変換・有限性チェック）を実装。不正レスポンスはスキップして影響を他銘柄へ広げない設計。
    - スコアは ±1.0 にクリップ。
    - ai_scores テーブルへの書き込みは部分失敗を考慮して、スコア取得済みコードのみ DELETE → INSERT（冪等）する実装。トランザクション制御（BEGIN/COMMIT/ROLLBACK）あり。
    - API キーは引数で注入可能（テスト容易性）、未設定時は環境変数 OPENAI_API_KEY を参照し未設定なら ValueError を送出。
    - Look-ahead バイアスを避けるため内部で date.today() / datetime.today() を参照しない。
  - regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - 処理フロー:
      - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッドを防止）
      - raw_news からマクロキーワードでフィルタしたタイトルを最大数取得
      - OpenAI（gpt-4o-mini）を用いてマクロセンチメントを評価（記事が無ければ LLM 呼び出しは行わず macro_sentiment=0）
      - リトライ・バックオフ、API エラー時のフェイルセーフ（macro_sentiment=0.0）を実装
      - レジームスコアを合成し閾値でラベル付け（_BULL_THRESHOLD / _BEAR_THRESHOLD）
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - OpenAI 呼び出しは外部の news_nlp とプライベート実装を分離してモジュール結合を避けている。
    - API キー注入対応、未設定時は ValueError。

- テスト性・堅牢性に関する実装上の配慮
  - OpenAI 呼び出しは _call_openai_api を分離しており、ユニットテスト時にパッチで置き換え可能。
  - API エラー（RateLimit, Connection, Timeout, 5xx）に対する共通のリトライ戦略とログ出力を実装。
  - DB 書き込みはトランザクションで保護し、失敗時は ROLLBACK を試みる。ROLLBACK に失敗した場合も警告ログを出す。
  - ルックアヘッドバイアス防止: 日付関連ロジックは外部からの target_date を基に動作し、内部で現在日時を参照しない設計。
  - DuckDB の互換性を考慮した実装（list バインドや executemany の仕様差分への対応）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- （現時点で特記すべきセキュリティ修正は無し）

Notes / 備考
- 一部の機能は J-Quants クライアント（kabusys.data.jquants_client）や quality モジュール等外部モジュールに依存するが、ETL・カレンダー・研究・AI 部分は DuckDB と OpenAI API を中心に単体で動作するよう設計されています。
- 実運用では OPENAI_API_KEY 等の機密情報は環境変数に設定し、.env ファイルの取り扱いには注意してください（.env.local によりローカル上書きが可能）。
- 既存テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）に依存する実装が多数あるため、DB スキーマの準備が必要です。