CHANGELOG
=========
すべての変更は「Keep a Changelog」に準拠して記載しています。  
バージョニングは SemVer に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-01
-------------------
初回公開リリース — KabuSys 日本株自動売買システムの基盤機能を実装しました。

Added
- パッケージ基礎
  - パッケージ初期化を追加（kabusys.__init__、__version__ = 0.1.0）。
  - モジュール公開（data, strategy, execution, monitoring）。

- 設定 / 環境管理（kabusys.config）
  - Settings クラスを実装し、環境変数から一元的に設定を取得（J-Quants / kabuステーション / Slack / DBパス / 監視しきい値 / システム環境など）。
  - .env ファイル自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサーを実装:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - インラインコメント取り扱い（クォート外のみ）。
    - protected（OS 環境変数保護）と override の挙動を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須変数未設定時は明示的に ValueError を送出する _require を実装。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を追加。

- AI（kabusys.ai）
  - news_nlp.score_news:
    - ニュースのタイムウィンドウ計算(calc_news_window) を実装（JST→UTC のウィンドウ変換を含む）。
    - raw_news と news_symbols を集約して銘柄毎にテキスト結合し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - バッチ処理（最大 _BATCH_SIZE=20）、1銘柄あたり記事数・文字数の上限トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API の 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。
    - レスポンス検証（JSON 抽出、results リスト、code/score の整合性、数値検証、スコアクリップ ±1.0）。
    - DuckDB への冪等な書き込み（該当コードのみ DELETE → INSERT、空リスト対策）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - regime_detector.score_regime:
    - ETF 1321 の 200日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによるニュース抽出、LLM 呼び出し（gpt-4o-mini）、リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 合成スコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - lookahead バイアス回避設計（target_date 未満のデータのみ使用）。

- Data プラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー取得/管理ロジックと API 統合フック（jquants_client）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - DB データがない場合は曜日（週末）ベースのフォールバック。DB 登録値があれば優先して使用。
    - calendar_update_job: 夜間バッチで J-Quants から差分取得・バックフィル・健全性チェックを行い、market_calendar を冪等保存。
  - pipeline / ETL:
    - ETLResult データクラスを実装（取得件数、保存件数、品質検査問題の収集、エラー一覧を保持）。
    - 差分更新・バックフィル・品質チェックの設計方針を反映（jquants_client / quality モジュールとの連携想定）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
    - 200日MA乖離・1/3/6ヶ月リターン、20日 ATR、出来高・売買代金指標、PER/ROE 等を計算。
    - データ不足時の None 処理、DuckDB 上でのウィンドウ関数利用による実装。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン算出）、calc_ic（スピアマンランク相関）、rank（同順位の平均ランク処理）、factor_summary（統計サマリー）を実装。
    - 外部依存なしで標準ライブラリのみで実装。lookahead バイアス回避に注意。

- その他
  - ロギングを多所に追加（重要な分岐やフォールバック、API エラー時の警告/情報ログ）。
  - DuckDB の互換性・安全性を考慮した実装（executemany の空リスト回避、日付型変換ユーティリティ等）。
  - モジュールエクスポート（__all__）整備によりパブリック API を明確化。

Changed
- 該当なし（初回リリース）。

Fixed
- 複数モジュールでフェイルセーフの振る舞いを明確化:
  - OpenAI API 呼び出し失敗時は例外を投げずに中立値（score=0.0 等）で継続する実装を適用。
  - DB 書き込み失敗時のトランザクションロールバック（ROLLBACK）とロギングを整備し、ROLLBACK 自体の失敗を警告ログで報告。

Security
- 環境変数未設定時は明示的に ValueError を送出する仕組みを導入（API キー等の必須設定漏れを早期に検出）。
- OS 環境変数を .env による上書きから保護するため protected キーセットを採用。

Notes / Known limitations
- OpenAI のモデルはデフォルトで gpt-4o-mini を使用する設定（将来的に変更の余地あり）。
- research モジュールは DuckDB の prices_daily/raw_financials のデータ前提。実行前に適切なデータ投入が必要。
- 一部 API クライアント（jquants_client）や quality モジュールは外部実装を前提としており、環境に応じたモックや実装が必要。
- 単体テストは _call_openai_api を patch して OpenAI 呼び出しをモックする設計になっている。

Authors
- KabuSys 開発チーム（リポジトリ内ソースコードに準拠）

--- 
（この CHANGELOG はコード内容からの推測に基づいて生成されています。実際の変更履歴・リリースノートと差異がある場合は適宜編集してください。）