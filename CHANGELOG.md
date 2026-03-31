Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
- なし

0.1.0 - 2026-03-31
Added
- 初回リリース: kabusys パッケージを公開。
  - パッケージバージョン: 0.1.0
  - パッケージ説明: 日本株自動売買システムのコアライブラリ（モジュール群: data, research, ai, execution, strategy, monitoring を想定）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local からの自動ロード機能を実装。プロジェクトルートの検出は .git または pyproject.toml を基準とするため、CWD に依存しない。
  - 強化された .env パーサ: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護機能: OS 環境変数を保護するための上書き制御（protected）。
  - Settings クラスを導入: J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを提供。未設定の必須変数は明示的な ValueError を送出。

- AI 関連 (kabusys.ai)
  - ニュース NLP (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとにテキスト結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換）を厳密に扱う（ルックアヘッド防止）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数のトリム制御、JSON Mode による厳密なレスポンス想定。
    - 再試行ロジック（429、ネットワーク断、タイムアウト、5xx を対象）とエラーフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - レスポンスバリデーション: JSON 抽出、results 配列・各要素の code/score 検証、スコアを ±1.0 にクリップ。
    - DuckDB への冪等的書き込み（DELETE → INSERT）を採用し、部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出し部をパッチ差替え可能に設計。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み70%）と、ニュースベースのマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - ma200 比率計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。データ不足時は中立（1.0）を採用。
    - マクロ記事抽出はタイトルのキーワードマッチ（デフォルトキーワード群あり）。
    - OpenAI 呼び出しのリトライ / バックオフ、API 失敗時は macro_sentiment=0.0（フォールバック）。
    - 計算結果を market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、失敗時は ROLLBACK を実行。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーを扱うユーティリティ群を提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未取得のときは曜日ベースのフォールバック（平日を営業日）を使用して堅牢に動作。
    - 夜間バッチ calendar_update_job を実装: J-Quants から差分取得 → 保存（バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル、先読み等の設定パラメータ実装。

  - ETL パイプライン (pipeline.ETLResult と etl の公開)
    - ETL 実行結果を保持する ETLResult データクラスを実装（フェッチ件数、保存件数、品質問題リスト、エラーリスト等）。
    - ETLResult に has_errors / has_quality_errors / to_dict を提供し、監査ログや上位ハンドリング用の情報整形をサポート。
    - pipeline モジュールおよび etl から ETLResult を公開。

- リサーチ/ファクター (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を DuckDB クエリで計算（営業日ベースのラグ）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily 組合せで PER / ROE を算出（EPS=0等は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部発注や本番 API にはアクセスしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を一括 SQL で取得。
    - calc_ic: スピアマン（ランク相関）による IC 計算。レコード数不足時は None を返す。
    - rank, factor_summary: ランク計算（同順位は平均ランク）や統計要約（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティ zscore_normalize を data.stats から再エクスポート。

Changed
- 設計方針・実装指針を明確化（各モジュールにコメントで設計意図を記載）。
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() の直接参照を避ける方針を一貫して採用。
  - OpenAI 呼び出し周りは各モジュールで独立実装し、モジュール間のプライベート関数共有を避けることで結合度を低減。
  - DB 書込みは可能な限り冪等性を担保（DELETE→INSERT パターン、トランザクション制御）。

Fixed
- （初回リリースのため主に実装完了。ランタイムでの失敗に備えたフェイルセーフ・ログ出力を多数追加。）

Known issues / Notes
- パーサー・API に依存する箇所
  - OpenAI API キー (OPENAI_API_KEY) は必須。未設定時は score_news / score_regime が ValueError を送出するため、バッチ運用時は環境変数設定を必ず行ってください。
- DB 書き込みロジック
  - DuckDB の executemany に空リストを渡せない制約に注意し、空チェックを実装済み（news_nlp）。
- 実装上の未完成・潜在的バグ（要注意）
  - pipeline モジュール末尾の _get_max_date 関数定義が途中で切れている箇所が存在します（ファイル末尾で "return date.fro" のような不完全なコード片で終端）。このままでは構文エラーや実行時例外となる可能性があるため、リリース前にこの関数の完成・テストが必要です。
- テスト設計
  - OpenAI 呼び出し部分はパッチ差替えを想定しているため、ユニットテストを容易に実装可能。ただし外部依存（DuckDB, J-Quants クライアント等）はモック化推奨。
- セキュリティ
  - .env ファイルの読み込み時にパスワード等の機密が環境変数としてセットされるため、運用時はファイル権限・デプロイ設定に注意してください。

Upgrade notes
- 本リリースは初版のため後続リリースで以下が想定されます:
  - pipeline の完結実装・品質チェック（quality モジュール）との連携強化
  - jquants_client モジュールの実装/テスト、および calendar_update_job の E2E テスト
  - execution / strategy / monitoring の具体的注文発注ロジック・監視アラート実装
  - エラー観測性向上のためのメトリクス・トレーシング追加

補足
- ログ出力や例外処理を多用しており、運用時のログ監視で異常検出がしやすい設計になっています。各機能は DuckDB 接続を引数として受け取ることで、テスト時にインメモリ DB を渡して検証可能です。

--- 以上 ---