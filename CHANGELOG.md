# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

なお、本CHANGELOGは提供されたコードベースから推測して作成しています（実装の意図・設計方針・未実装箇所なども含む）。

## [Unreleased]

### 注意事項
- 本リポジトリには一部実装が途中で切れている箇所（例: pipeline._get_max_date の末尾が途中で途切れているように見える）が存在します。リリース前に当該部分の完成・テストを推奨します。

---

## [0.1.0] - 2026-04-01

初回公開リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ骨子
  - kabusys パッケージの初期公開。top-level の __all__ に data, strategy, execution, monitoring を設定。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの強化:
    - "export KEY=val" 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォートあり/なしでの差分処理）
  - Settings クラスを提供（環境変数からアプリ設定を取得するプロパティ群）:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/監視閾値/ログ・実行環境等の設定
    - env, log_level のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev の便宜プロパティ
  - 必須変数未設定時に ValueError を投げる _require ヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI (gpt-4o-mini) によりセンチメントを算出して ai_scores テーブルへ書き込む。
    - 時間ウィンドウ: JST 基準で前日 15:00 ～ 当日 08:30（内部は UTC naive datetime に変換）。
    - バッチ処理: 1 API 呼び出しにつき最大 20 銘柄（_BATCH_SIZE）。
    - 1銘柄あたり最大記事数 / 最大文字数でトリム（トークン膨張対策）。
    - API リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証: JSON 抽出、results 配列検証、スコア数値化、既知コードのみ採用、スコア ±1.0 でクリップ。
    - DB への書き込みは部分失敗を考慮して、書き込み対象コードのみ DELETE → INSERT で上書き（冪等性確保）。DuckDB の executemany 空リスト制約に配慮。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で分離し、テストからモック可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei インデックス連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - prices_daily から ma200_ratio 計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしてタイトルを抽出、OpenAI (gpt-4o-mini) で JSON 出力（{"macro_sentiment": x}）を期待して評価。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）および ROLLBACK 対応。
    - リトライ・バックオフ、JSON パースの堅牢化、ログ出力を実装。
    - テスト容易性: _call_openai_api をモック可能に分離。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants からの差分取得と冪等保存（save_market_calendar 経由）を実行。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - カレンダー未取得時は曜日ベース（平日のみ営業日）でのフォールバックを提供。
    - バックフィルと健全性チェック（未来日異常検出）を実装。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETL の骨組みを実装。差分更新、保存（jquants_client の save_* を使用）、品質チェック（kabusys.data.quality を利用）等の設計に対応。
    - ETLResult データクラスを定義（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETLResult.to_dict() による辞書化をサポート（quality_issues を辞書リスト化）。
    - 一部ユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - ETLResult の再エクスポート (kabusys.data.etl)
    - pipeline.ETLResult を etl モジュールで再エクスポート。

- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播に配慮。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 や NULL の場合は None）。
    - DuckDB 上で SQL を用いて効率的に実行（外部 API へはアクセスしない設計）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて計算。ホライズン検証（1〜252）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコード（>=3）で計算。
    - rank: 同順位は平均ランクを採るランク化実装（丸めを用いて ties の誤差を防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### Security
- 現時点で機密情報は環境変数から読み込む設計。自動ロード時に OS 環境変数を保護する仕組み（.env の上書き制御）を導入。

### Design / Reliability / Testability
- ルックアヘッドバイアス対策: 各 AI / Research モジュールは datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を明示する設計。
- API 呼び出しは例外に強く、LLM/ネットワーク失敗時はフェイルセーフ（0.0 / スキップ）で継続する実装が多く含まれる。
- OpenAI 呼び出しは専用の内部関数に分離し、ユニットテスト時に簡単にモック可能。
- DuckDB を主なデータストア/計算基盤として採用し、SQL と Python を組み合わせた実装。
- DB 書き込みは冪等性・部分失敗保護を意識した設計（DELETE→INSERT、トランザクション、ROLLBACK のログ）。

### Known issues / TODO
- pipeline._get_max_date 関数の末尾が途中で切れている（提供されたコードが途中で終端しているため推測）。リリース前にこの関数の完成と関連ユニットテストの追加を推奨します。
- strategy / execution / monitoring の具体実装は本リリース時点でトップレベルに露出されているが、各サブモジュールの実装有無・完成度に差がある可能性があるため、利用前に確認してください。

---

参考: 各モジュールは詳細なログ出力を行うよう設計されています。運用時は LOG_LEVEL 等の設定を適切に行ってください。