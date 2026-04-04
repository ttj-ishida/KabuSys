# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース: 0.1.0（初期リリース）

[Unreleased]

## [0.1.0] - 2026-04-04

### Added
- 基本パッケージ初期公開
  - パッケージ名: kabusys, バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルート判定は .git / pyproject.toml ベース）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装：export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応
  - 上書き制御（override/protected）をサポートし、OS 環境変数を保護
  - Settings クラスで各種設定プロパティを提供（必須 env の取得は _require により ValueError を送出）
    - J-Quants、kabuステーション、LINE、DuckDB/SQLite パス、監視用ファイルパス、CPU/MEM/DISK閾値、環境（development/paper_trading/live）、ログレベル等
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）でセンチメントを取得
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算済み）
      - 1 銘柄あたり記事数と文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトリム
      - バッチ処理（最大 20 銘柄/コール）、JSON mode を利用したレスポンス検証
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ
      - レスポンスの厳密なバリデーション（results 配列・型・既知コード・数値検査）
      - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT、DuckDB の executemany 制約に配慮）
      - API キー注入可（api_key 引数または環境変数 OPENAI_API_KEY）
      - テスト用フック: _call_openai_api を patch して差し替え可能
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロ経済ニュースの LLM センチメントを加重合成（MA 70% / Macro 30%）
      - マクロキーワードに基づく raw_news 抽出（最大記事数制限）
      - OpenAI 呼び出し（gpt-4o-mini）とリトライ/フェールセーフ（API 失敗時は macro_sentiment=0.0）
      - レジームスコアのクリップとラベル付与（bull / neutral / bear）
      - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理
      - lookahead バイアス対策: target_date 未満のデータのみ参照、datetime.today() を参照しない設計
      - テスト用フック: _call_openai_api を patch で差し替え可能

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスで ETL の取得・保存数、品質問題一覧、エラーを集約
    - 差分更新・バックフィル・品質チェックの設計方針を反映
    - jquants_client（外部）を用いた取得・保存処理に対応
    - DuckDB を前提とした実装（テーブル存在チェック等ユーティリティ）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定・SQ 判定
    - 関数群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - カレンダーデータが無い/部分的な場合の曜日ベースフォールバック（週末は非営業日）
    - calendar_update_job による J-Quants からの差分取得・保存（バックフィル・健全性チェック・ON CONFLICT 相当の保存）
    - 最大探索範囲の制限（無限ループ防止）
  - ETL インターフェース再エクスポート（kabusys.data.etl: ETLResult）

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB SQL を活用した高速集計、データ不足時の None 処理
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）
    - calc_ic: スピアマン（ランク）相関による IC 計算（同順位は平均ランクで処理）
    - rank: 同順位考慮のランク化（丸めで ties 対策）
    - factor_summary: count/mean/std/min/max/median の統計サマリー
  - research パッケージは zscore_normalize（kabusys.data.stats 内）も再エクスポート

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Internal / 設計上の重要点（ドキュメント的補足）
- 全体的に「ルックアヘッドバイアス防止」を重視
  - datetime.today() / date.today() をスコア計算やデータ選定に直接参照しない設計
  - DB クエリでは target_date 未満/指定範囲の明示的条件を使用
- OpenAI 呼び出しまわりはフォールバック設計
  - リトライ（指数バックオフ）を実装し、最終的に API が使えない場合も処理を継続（ゼロスコアやスキップ）
- DB 書き込みは冪等性を重視（DELETE→INSERT / ON CONFLICT 相当の扱い）
- DuckDB の executemany に対する注意（空リストを渡さない対策）を反映
- テスト容易性のため、API 呼び出し関数はモジュール単位で差し替え可能に実装
- 一部機能は想定通り未実装/制限あり（例: calc_value の PBR・配当利回りは未実装）

### Known requirements / 注意事項
- OpenAI API（gpt-4o-mini）を利用する機能は OPENAI_API_KEY が必要（api_key 引数で注入可能）
- J-Quants 関連は JQUANTS_REFRESH_TOKEN 等の環境変数を使用
- Kabusys は DuckDB をデータ格納・分析の中心として利用
- 本リリースは主に分析/リサーチ・データ基盤・AI スコアリングの実装が中心で、発注/実行ロジック（execution モジュール）や本番監視の統合は別途実装・連携が想定される

---

（注）この CHANGELOG は提供されたコードベースから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて調整してください。