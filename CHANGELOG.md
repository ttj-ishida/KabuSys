# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買／データ基盤のコア機能をまとめて実装しました。主な追加点と設計上の注意点を以下に示します。

### Added
- パッケージの基本情報
  - パッケージ名: KabuSys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パブリックサブパッケージのエクスポート: data, strategy, execution, monitoring。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルートから自動読み込みする仕組み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env の行パーサを実装（コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ対応）。
  - 環境変数取得ヘルパ（Settings クラス）。J-Quants、kabuステーション、LINE、DB パス、paper trading 設定、監視閾値、ログレベル、ランタイム環境判定（development/paper_trading/live）等のプロパティを提供。
  - 必須環境変数未設定時は明示的に ValueError を送出するユーティリティ _require。

- AI 関連: ニュース NLP とレジーム判定（src/kabusys/ai/）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）の JSON モードでバッチ判定。
    - バッチ処理（最大 20 銘柄/回）、各銘柄は最大記事数・文字数でトリム（過大トークン対策）。
    - 429・ネットワーク断・タイムアウト・5xx について指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアクリップ）。
    - 成功分のみを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に既存データを保護。
    - calc_news_window: target_date に対するニュース収集ウィンドウ（JSTベースで UTC に変換）を提供。
    - テストしやすさのため、OpenAI 呼び出しの内部関数は差し替え可能（unittest.mock.patch を想定）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（70% 重み）と news_nlp によるマクロセンチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは独立実装でモジュール結合を避ける。API 失敗時は macro_sentiment=0.0 として継続。
    - レジーム合成、閾値に基づくラベル付与、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しでの再試行（RateLimit/接続/タイムアウト）や 5xx 判定の取り扱いを実装。

- データ基盤（src/kabusys/data/）
  - calendar_management
    - JPX カレンダー管理 API 連携用ジョブ calendar_update_job を実装（J-Quants から差分取得 → market_calendar へ冪等保存）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB にデータがない場合は曜日（土日）ベースのフォールバックを使用。
    - 最大探索範囲やバックフィル、健全性チェック（過度に未来の日付はスキップ）など保護ロジックを実装。
  - ETL パイプライン（pipeline.ETLResult を含む）
    - ETLResult データクラスで ETL の集計結果（取得数/保存数/品質検査結果/エラー）を表現。
    - ETL 実行フロー設計に基づく差分更新、バックフィル、品質チェックの方針を反映。
  - etl.py で ETLResult の再エクスポート。

- 研究用ユーティリティ（src/kabusys/research/）
  - factor_research
    - calc_momentum: mom_1m/3m/6m、ma200乖離（ma200_dev）等を DuckDB SQL で効率的に計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務（eps, roe）を取得して PER/ROE を計算。
    - 全関数は prices_daily / raw_financials のみ参照し、本番取引 API にアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）について将来リターンを計算。ホライズン検証（1〜252）あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクとして扱うランク計算。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### Changed / Design decisions（実装上の主な方針）
- ルックアヘッドバイアス回避
  - 各処理（news, regime, research 等）は内部で datetime.today() / date.today() を直接参照せず、必ず target_date を明示的に受け取る設計。DB クエリは target_date 未満／排他条件等を使いルックアヘッドを防止。
- フェイルセーフ設計
  - AI API の失敗時は例外で全体を止めず、0.0 や空スコアなどのデフォルトにフォールバックして続行する箇所を用意（ログ出力を伴う）。部分失敗時にも DB 内の他データを保護するため、書き込み対象コードを限定して置換。
- テスト容易性
  - OpenAI 呼び出し部分は内部関数で切り出し、テスト時に patch して差し替え可能（ユニットテストで外部 API をモックしやすい）。
- DB 互換性配慮
  - DuckDB バインドの互換性（executemany に空リストを与えない等）に注意した実装。

### Fixed
- （初版のため該当なし）

### Security
- 必須 API キー（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）が未設定の場合は明示的にエラーを出す設計。自動ロード設定や OS 環境変数の保護（.env の上書き禁止）機構を実装。

### Known limitations / Notes
- news_nlp/regime_detector は OpenAI の JSON Mode（gpt-4o-mini）を利用するため、API レスポンス形式に依存する。レスポンスのパースで堅牢性を高めているが、将来的に API 仕様が変わると調整が必要。
- research モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB SQL で実装しているため、大規模データでのパフォーマンス評価は今後の課題。
- strategy / execution / monitoring パッケージはエクスポートされているが、本リリースでは主にデータ・研究・AI 関連のコア機能を重点実装。

---

開発チームへ:
- 追加・修正点が出たら本 CHANGELOG を更新してください（Unreleased セクション → 新バージョンへ移動）。