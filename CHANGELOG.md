# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-26

初期リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの公開インターフェースを追加（data, strategy, execution, monitoring を __all__ で公開）。
  - パッケージバージョンを 0.1.0 として設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 自動ロードの無効化を行う環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパースを強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートの有無に応じた判定）
  - .env ロード時に OS 環境変数を保護する仕組み（protected set）。
  - 必須環境変数チェック用の _require 実装。以下の主要キーを必須として取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 各設定のデフォルト値や検証（例: KABUSYS_ENV は development/paper_trading/live のみ有効、LOG_LEVEL は標準ログレベルのみ許可）。
  - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）および Path 型での取得。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出する機能を実装（score_news）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
    - バッチ処理: 最大 _BATCH_SIZE(=20) 銘柄ずつ API に送信、1銘柄あたりの記事上限・文字数上限でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用したレスポンス期待、レスポンスのバリデーション・抽出ロジック実装（_validate_and_extract）。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで行い、APIエラーはフェイルセーフによりスキップして継続。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時の保護）。
    - 外部副作用を最小化する設計（datetime.today() などを参照しない、テスト容易性のため _call_openai_api を差し替え可能）。

  - マーケットレジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定（score_regime）。
    - ma200_ratio の計算（_calc_ma200_ratio）においてルックアヘッドバイアスを防ぐため target_date 未満のデータのみを使用し、データ不足時は中立（1.0）でフォールバック。
    - マクロ記事抽出（_fetch_macro_news）と LLM によるマクロセンチメント評価（_score_macro）を実装。
    - OpenAI API 呼び出しはモデル gpt-4o-mini、JSON 期待。API エラーは最大リトライを行い、最終的に失敗した場合は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 合成スコアは clip(-1..1) され閾値に基づきラベル付け。結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データモジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー操作ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得して market_calendar に冪等保存。バックフィル/健全性チェックを含む。
    - 最大探索範囲制限や date 型一貫性（timezone 混入防止）を担保。

  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - 差分取得→保存→品質チェックという ETL フローを実装する基礎を提供。
    - ETLResult データクラスを定義し、etl モジュールで公開（ETLResult を再エクスポート）。
    - 最終取得日の算出、テーブル存在チェック、バックフィル、品質チェックのためのインフラを実装。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - Value（PER, ROE を raw_financials から取得）
    - Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比）
    - 各関数は DuckDB SQL により prices_daily/raw_financials を参照して結果を返す（(date, code) キーの dict リスト）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）での将来リターンを計算。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関によりファクター有効性を評価。
    - ファクター統計サマリー（factor_summary）およびランク変換ユーティリティ（rank）。
  - データ統計ユーティリティ zscore_normalize を data.stats から再エクスポート。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能。環境変数 OPENAI_API_KEY の未設定時は ValueError を発生させることで誤った無認証呼び出しを防止。
- .env 自動ロード時に OS 環境変数を保護するロジックを導入（既存キーの上書きを制御）。

### Notes / Implementation details
- DuckDB を主要な分析データストアとして想定（全ての data/research/ai モジュールは DuckDB 接続を受け取る設計）。
- LLM 呼び出し関連はテスト容易性のため差し替え用の内部関数（_call_openai_api）を用意。
- ルックアヘッドバイアス防止のため、日付参照は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計原則を採用。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 等）で行い、部分失敗時に既存データを不必要に消さないよう配慮。

今後の改善候補（未実装/検討事項）
- PBR・配当利回りなどのバリューファクターの追加実装。
- 更に詳細なログ・監視（monitoring モジュールの充実）。
- OpenAI 呼び出しのメトリクス収集（レイテンシ/エラー率）。
- ETL の並列化および障害時のリトライポリシーの強化。