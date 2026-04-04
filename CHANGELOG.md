# Changelog

すべての重要な変更点をこのファイルで管理します。本ファイルは "Keep a Changelog" の形式に準拠します。

## [0.1.0] - 2026-04-04

初回リリース。

### Added
- パッケージ初期実装: kabusys (__version__ = 0.1.0) を追加。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を想定（__all__ に列挙）。

- 環境変数・設定管理 (kabusys.config)
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出し、CWD に依存しない検索を実装。
  - .env ファイル自動読み込み: 読み込み順序は OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - コメント処理（クォートなしでは '#' の直前がスペース/タブである場合をコメントと判断）を実装。
    - 無効行のスキップ。
  - 上書き保護:
    - .env 読み込み時に既存の OS 環境変数を保護する protected ロジックを実装（.env.local で上書き可）。
  - Settings クラスを提供:
    - 各種必須・任意設定プロパティ: J-Quants/LINE/kabu API 関連、DB パス（DuckDB/SQLite）、監視用ファイルパス、CPU/Memory/Disk のしきい値、環境 (development/paper_trading/live)、ログレベル検証など。
    - 必須項目未設定時は ValueError を送出する _require() を利用。

- ニュース NLP / マクロレジーム検出 (kabusys.ai)
  - ニュースセンチメント解析 (kabusys.ai.news_nlp.score_news)
    - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を実装（UTC naive datetime を返す）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、記事数・文字数上限でトリム。
    - OpenAI（gpt-4o-mini, JSON mode）へバッチ送信（_BATCH_SIZE=20）。リトライ（429、ネットワーク断、タイムアウト、5xx）と指数バックオフを実装。
    - レスポンス検証とスコアの ±1.0 クリップ。JSON の前後雑多テキストを修復する処理も含む。
    - DuckDB の ai_scores テーブルへ「部分失敗で既存データを保護する」方針で DELETE → INSERT による置換を実施。DuckDB の executemany の制約（空リスト不可）を考慮。
    - API キー解決ロジック: 引数優先、引数が None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。

  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321（Nikkei 225 連動 ETF）の直近 200 日移動平均乖離を計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）。
    - マクロ経済ニュース（タイトルベース）を抽出し、OpenAI でマクロセンチメントを評価（記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0）。
    - MA（70%）とマクロ（30%）の重みでスコア合成し -1..1 にクリップ、閾値に基づいて 'bull'/'neutral'/'bear' ラベルを決定。
    - DuckDB の market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。エラー時は ROLLBACK を試行し、失敗ログを記録。

- 研究 (research) モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（平均）、ATR 比率、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS 0/欠損時は None）。
    - 設計方針として DuckDB の prices_daily / raw_financials のみ参照し、実際の発注等へは影響しない独立実装。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を一括 SQL で取得。
    - calc_ic: スピアマンランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクとして扱う実装（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出。
  - research パッケージから関連関数を再エクスポート（zscore_normalize 等も含む）。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にデータがない/未登録日の場合は曜日ベース（土日非営業）でフォールバックし、一貫性を保つ実装。
    - calendar_update_job: J-Quants クライアント経由で差分取得・保存（バックフィル・健全性チェックを実装）。保存は jquants_client の保存関数を利用。
  - pipeline / etl:
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題・エラー概要を保持）。to_dict() で品質問題を辞書化。
    - ETL 流れの設計（差分更新・保存・品質チェック・バックフィル）とユーティリティ関数を提供。
    - _table_exists / _get_max_date 等の DB ユーティリティを実装。
  - data.etl: ETLResult を公開インターフェースとして再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境変数を保護する仕組みを導入（.env による上書きを制御）。OpenAI API キー等の扱いは明示的に引数か環境変数で解決し、未設定時はエラーで明示することで誤った無効な実行を防止。

### Notes / Design decisions（重要な設計上の注意）
- ルックアヘッドバイアス防止: 解析・スコアリング系関数は datetime.today()/date.today() を参照して内部で日付を決めない設計（target_date を明示的に渡す）。
- API 呼び出しの堅牢性: OpenAI 呼び出しはリトライ・バックオフ・5xx 判定・非致命的エラー時のフォールバック（0.0 スコアやスキップ）を行い、ETL/解析処理を継続するフェイルセーフを採用。
- DuckDB トランザクション: 書き込みは冪等性を意識した DELETE → INSERT パターンと BEGIN/COMMIT/ROLLBACK を用いた安全性確保を行う。
- テスト容易性: OpenAI 呼び出しなど外部依存箇所は内部関数をモック可能に設計。

（今後）
- strategy / execution / monitoring モジュールの具体的実装・公開 API の拡充予定。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に沿った追加実装・テストを継続予定。

---

参考: 各モジュールの詳細実装はソース内ドキュメンテーション（docstring）に記載されています。必要であれば特定モジュール・関数の変更履歴や設計理由をさらに分割して記載します。