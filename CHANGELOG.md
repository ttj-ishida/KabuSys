Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」フォーマットに従います。  

フォーマット
-----------
通常のセクション: Added, Changed, Deprecated, Removed, Fixed, Security

Unreleased
----------
（現在無し）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース。
- パッケージ構成
  - kabusys パッケージ本体（src/kabusys）
  - サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に公開）
- 環境設定・自動 .env 読み込み（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - 読み込み順序: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応したパーサ実装
  - 必須環境変数取得ヘルパー _require を提供
  - 主要環境変数（例）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV（development/paper_trading/live 判定用）、LOG_LEVEL（DEBUG/INFO/...）
- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ問い合わせして銘柄別センチメント（ai_scores）を生成・書き込み
    - タイムウィンドウ（JST 前日15:00〜当日08:30 相当）計算ユーティリティ calc_news_window を提供
    - バッチサイズ制御、記事数/文字数トリム、レスポンス検証、スコアの ±1.0 クリップを実装
    - レート制限・ネットワーク断・5xx に対する指数バックオフリトライ、失敗時は個別チャンクスキップ（フェイルセーフ）
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api の patch 対応）
  - regime_detector.score_regime
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）と news_nlp 由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・market_regime テーブルへ冪等書き込み
    - マクロニュース抽出用キーワードリスト、LLM 呼び出し（gpt-4o-mini）、JSON パース、リトライ/フォールバック（API失敗時 macro_sentiment=0.0）
    - look-ahead バイアス防止設計（target_date 未満データのみ利用、datetime.today() を参照しない）
- Research モジュール（src/kabusys/research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（必要行数不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - calc_value: PER, ROE（raw_financials から最新財務データを取得）
    - DuckDB を用いた SQL ベースの実装。結果は (date, code) をキーとする dict リストで返却
  - feature_exploration
    - calc_forward_returns: 複数ホライズンに対する将来リターン算出（horizons 検証あり）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（結合・欠損除外・最小レコード検査）
    - rank: 同順位は平均ランク扱い（丸めで ties 判定安定化）
    - factor_summary: count/mean/std/min/max/median の集計
  - research パッケージは kabusys.data.stats の zscore_normalize を再利用
- Data モジュール（src/kabusys/data）
  - calendar_management
    - JPX カレンダー管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - market_calendar が未取得のときは曜日ベースでフォールバック。DB 登録値優先で一貫した振る舞いを保証
    - calendar_update_job: J-Quants API から差分取得 → jq.save_market_calendar を呼んで冪等保存。バックフィル・健全性チェック実装
  - pipeline / etl / ETLResult
    - ETLResult データクラス: ETL 実行結果の集約（取得数/保存数/品質問題/エラー等）と to_dict メソッド
    - ETL パイプライン方針（差分更新、backfill、品質チェックを収集し続ける設計）
  - jquants_client 経由でのデータ取得・保存を想定（jq.* の利用）
- テストしやすさ・堅牢性設計
  - OpenAI 呼び出し点を個別関数として切り出しテスト時にモック差し替え可能
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT または executemany で冪等性を意識
  - ルックアヘッドバイアス回避（日時参照の明示的回避）・フェイルセーフ（API失敗時のデフォルト）を重視
- ドキュメント的な docstring が各モジュールに充実（処理フロー、設計方針、返り値・例外仕様を明記）

Changed
- 初回リリースのため過去バージョンとの差分は無し。

Fixed
- 初回リリースのため無し。

Removed
- 初回リリースのため無し。

Deprecated
- 初回リリースのため無し。

Security
- OpenAI API キーは引数で注入可能。環境変数 OPENAI_API_KEY も利用可能。キー管理は利用者側の責任。

Known issues / 注意点
- DuckDB のバージョンに依存する結合・配列バインドの挙動に配慮した実装（executemany を用いた逐次 DELETE 等）を行っているが、実環境での互換性確認を推奨。
- raw_news / prices_daily / ai_scores / market_regime / raw_financials / news_symbols / market_calendar 等のテーブルスキーマは本リポジトリ外に定義されていることを想定。初期導入時にスキーマ準備が必要。
- OpenAI 呼び出しで想定外のレスポンス形式が来た場合は該当チャンクをスキップして続行する設計（部分失敗を許容）。運用時はログ監視・再実行ポリシーの整備を推奨。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出し実装を持ち、内部の private 関数はモジュール間で共有しない設計（意図的な分離）。

作者・貢献方法
- 初回リリース。バグ報告・機能要求は issue を作成してください（詳細な再現手順・ログを添付いただけると助かります）。

-----