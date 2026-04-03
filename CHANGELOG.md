# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

- リリースはセマンティックバージョニングに従います。
- このプロジェクトの初期バージョンは 0.1.0 です。

## [Unreleased]
- 次回リリースに向けた変更・修正はここに記載されます。

## [0.1.0] - 2026-04-03
初回公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージの公開モジュール群を整理（data, strategy, execution, monitoring を __all__ で公開）。
  - __version__ を "0.1.0" として設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後の動作を想定）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - 行末コメントの取り扱い（クォートの有無による判定）を実装。
  - 環境変数取得ユーティリティ（Settings クラス）を提供。J-Quants / kabuAPI / LINE / データベース / 監視 / システム関連の設定プロパティを含む。
  - 必須変数未設定時は ValueError を送出する _require() を提供。
  - KABUSYS_ENV, LOG_LEVEL の検証ロジックを実装（許可値チェック）。

- データ処理（kabusys.data）
  - ETL ユーティリティ公開インターフェース（ETLResult を再エクスポート）。
  - ETL パイプライン（data.pipeline）:
    - 差分取得・保存・品質チェックの流れを表現する ETLResult データクラスを実装。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得などのユーティリティ基盤を実装（ETL 基盤）。
  - マーケットカレンダー管理（data.calendar_management）:
    - market_calendar テーブルを使った営業日判定・前後営業日取得・期間内営業日リスト取得（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日（平日）ベースでフォールバックする一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得 → 冪等保存（save_market_calendar）を実施。バックフィル・健全性チェックを実装。

- 研究用（kabusys.research）
  - ファクター計算（research.factor_research）:
    - モメンタム（1M/3M/6M リターン）、200日移動平均乖離、ATR（20日）、出来高/売買代金関連などを DuckDB 上の SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - prices_daily / raw_financials のみ参照し本番発注系へ影響しない設計。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関）。
    - ランク変換（rank: 同順位は平均ランク）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - research パッケージで必要な関数を __all__ で公開。data.stats の zscore_normalize を再エクスポート。

- AI / NLP（kabusys.ai）
  - ニューススコアリング（ai.news_nlp）:
    - raw_news + news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI GPT 系モデル（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む（score_news）。
    - JST 時間ウィンドウを UTC に変換して安全なウィンドウ計算を実装（calc_news_window）。
    - 1チャンク最大 20 銘柄、1銘柄あたり記事数・文字数制限（トリム）を実装してトークン肥大化を防止。
    - OpenAI 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対するエクスポネンシャルバックオフ）。
    - JSON Mode のレスポンスを検証・復元（前後余計なテキストの除去）し、取得スコアを ±1.0 にクリップ。
    - 部分失敗に備え、書き込みは対象コードのみ DELETE → INSERT することで既存データを保護。
    - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定（ai.regime_detector）:
    - ETF 1321（Nikkei 225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定（score_regime）。
    - prices_daily から ma200_ratio を計算、raw_news をマクロキーワードでフィルタして OpenAI に投げるフローを実装。
    - API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフ。
    - DB への書き込みは冪等に（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK を試行して例外を伝播。

### Changed
- （初回リリースのため該当なし）今後のリリースで変更点を明記予定。

### Fixed
- 実装上の堅牢化・互換性対応
  - DuckDB の executemany に関する制約対応（空リストでの executemany を避けるガードを追加）。
  - OpenAI レスポンスの多様なエラーケースに対するログ出力とフォールバック（JSON パース失敗・非 5xx エラー・5xx のリトライ制御など）。
  - market_calendar の NULL 値検出時は警告を出し曜日フォールバックに戻る安全設計を採用。

### Security
- OpenAI API キーやその他機密情報は環境変数で管理する設計。設定取得で必須が未設定の場合は明示的に ValueError を発生させることで誤動作を防止。

### Design / Implementation notes（設計上の重要事項）
- ルックアヘッドバイアス対策:
  - AI モジュール（news_nlp, regime_detector）、研究関数等は内部で datetime.today()/date.today() を参照せず、外部から与えられる target_date を厳密に使う設計。
  - DB クエリは target_date 未満・以前のデータを明示的に扱い、将来情報の混入を防止。
- 冪等性:
  - 外部データの保存は可能な限り冪等（DELETE→INSERT / ON CONFLICT DO UPDATE）で実装。
- フェイルセーフ:
  - API 呼び出し失敗時は例外を直ちに投げず、可能な限り処理を継続して部分的な結果を残す（監視ログやエラー一覧で上位が判断できる設計）。

---

この CHANGELOG はソースコードからの推測に基づき作成しています。実際のコミット履歴や開発ノートがあれば、それらに基づいてより正確に更新してください。