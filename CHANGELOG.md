CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に従っています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。
  - パッケージ初期化: kabusys パッケージのエクスポートを定義（data, strategy, execution, monitoring）。
  - 設定管理モジュール (kabusys.config)
    - .env ファイルおよび環境変数からの自動読み込み実装（プロジェクトルート判定：.git / pyproject.toml）。
    - .env パーサ実装：export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープの処理、インラインコメント処理。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数チェック（_require）、設定プロパティ群（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル検証）。
    - デフォルト値（KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV/LOG_LEVEL のバリデーション）。
  - AI モジュール (kabusys.ai)
    - news_nlp: ニュース文章を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込むワークフロー。
      - ニュース時間ウィンドウ計算（JST → UTC 変換）、銘柄ごと記事集約、トークン肥大対策（記事数・文字数制限）、バッチ処理（最大20銘柄/バッチ）。
      - API レスポンスの厳密な JSON 検証と復元ロジック（前後余計なテキストの切り出し）。
      - 再試行（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、失敗時はフェイルセーフでスキップ。
      - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時の既存データ保護）。
    - regime_detector: ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - ma200 計算（ルックアヘッド防止のため target_date 未満データ使用）、マクロ記事抽出、LLM 呼び出し（JSON mode）、再試行・フェイルセーフ設計。
      - 計算結果を market_regime テーブルへ冪等書き込み。
  - Data モジュール (kabusys.data)
    - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - market_calendar テーブルがない場合は曜日ベースでフォールバック。
      - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動。
      - 夜間バッチ calendar_update_job: J-Quants から差分取得→保存、バックフィルと健全性チェック。
    - pipeline / etl:
      - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラー管理）。
      - 差分取得・バックフィル・品質チェック・冪等保存の設計方針に従った ETL 基礎実装。
    - jquants_client を想定した差分フェッチ連携ポイントや品質チェックフックを設計。
  - Research モジュール (kabusys.research)
    - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算を実装（prices_daily / raw_financials のみ参照）。
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR・相対 ATR・20日平均売買代金・出来高比率。
      - calc_value: PER（EPS が 0/欠損時は None）、ROE（最新財務レコードの取得ロジック）。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）。
      - 外部依存を持たない純粋な実装。ランクは同順位を平均ランクで扱う（丸めで ties 対策）。
  - さまざまなログ出力（情報/警告/デバッグ）を通じた観測性強化。

Changed
- API 呼び出し関連の設計方針を明文化:
  - datetime.today() / date.today() を直接参照せず、target_date ベースで処理することでルックアヘッドバイアスを防止。
  - OpenAI とのやり取りは JSON Mode を期待しつつ、実運用上のノイズに対する復元処理を実装。
- DuckDB への書き込み時の互換性対応:
  - executemany に空リストを渡さない保護（DuckDB 0.10 の制約回避）。
  - list 型バインドに依存しない削除ロジック（個別 DELETE を繰り返す）を採用。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理ルールの明確化。
  - 読み込み失敗時に warnings.warn を出すようにして静かな失敗を抑制。
- OpenAI 呼び出し・レスポンス処理の回復力強化:
  - レート制限 / ネットワーク断 / タイムアウト / 5xx に対するリトライ（指数バックオフ）を実装。
  - API エラーやパース失敗時は例外を上位へ投げずにフェイルセーフ値（例: macro_sentiment=0.0）や空スコアで継続する設計。
- calendar_update_job と calendar 周りの健全性チェック実装:
  - last_date が過度に将来日付の場合はスキップしてログ警告。
  - バックフィル範囲の明示と lookahead のパラメータ化。

Security
- 環境変数上書き保護:
  - 自動 .env 読み込み時に既存 OS 環境変数を protected として保護（.env.local は上書き可能だが OS 環境変数は除外）。
- OpenAI API キーは引数で注入可能（テスト性向上）かつ環境変数 OPENAI_API_KEY にフォールバック。キー未設定時は ValueError を明示。

Notes / Important
- このリリースは「データ取得・特徴量計算・ニュース/レジームのAIスコアリング・カレンダー管理」を中心とした基盤実装です。実際の発注ロジック（execution）や運用用監視（monitoring）、戦略（strategy）の具体実装は別モジュール／今後のリリースで追加される想定です。
- 期待される DuckDB テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が存在することを前提に動作します。テーブルスキーマの整合性は呼び出し側で確保してください。
- デフォルトの DB パスは DUCKDB_PATH= data/kabusys.duckdb、SQLite は data/monitoring.db。必要に応じて環境変数で上書きしてください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）起点で行うため、配布後やテスト時に問題がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

互換性（Breaking Changes）
- 初期リリースのため過去バージョンとの互換性に関する記述はありません。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装および統合テスト追加。
- E2E 用のテストデータセットと CI ジョブでの DuckDB スキーマ検証。
- AI モジュールの評価・チューニングとキャッシュ戦略の追加。