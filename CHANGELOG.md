Keep a Changelog
=================

すべての重要な変更履歴をここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

Unreleased
----------

- なし

0.1.0 - 2026-03-29
------------------

Added
- 初期リリース: kabusys パッケージの基本機能を実装。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パッケージルート: src/kabusys/__init__.py（公開モジュール: data, research, ai, ...）

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動ロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
  - .env パーサー実装:
    - export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理。
  - 環境変数取得ユーティリティ Settings を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証。
    - デフォルトの DB パス: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
    - ヘルパープロパティ: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news, news_symbols テーブルのデータを、OpenAI（gpt-4o-mini、JSON Mode）でバッチ解析して銘柄ごとのセンチメントを ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。
    - バッチ/トークン制御: 1回で最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフ（最大リトライ数を実装）。
    - レスポンス検証: JSON パース、results 配列・各要素の code/score 検証、数値変換、±1.0 にクリップ。
    - 部分失敗耐性: 成功した銘柄のみ ai_scores を置換（DELETE → INSERT）し、部分失敗で既存スコアを消さない実装。
    - テスト容易性: OpenAI 呼び出し箇所は差し替え可能（ユニットテスト用フックに配慮）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
    - マクロニュース抽出はニュースタイトルをマクロキーワードでフィルタ（キーワードリストはモジュール内定義）。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を期待。API エラーやパースエラー時のフェイルセーフとして macro_sentiment=0.0 を採用。
    - ルックアヘッドバイアス防止: datetime.today()/date.today() を参照せず、prices_daily の date < target_date を明確に指定。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を試みて例外を上位へ送り返す。

- データ基盤モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使用した営業日判定と操作ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録がない場合は曜日（平日）ベースのフォールバックを行う設計。
    - 最大探索範囲（_MAX_SEARCH_DAYS）や先読み・バックフィルのポリシーを実装。
    - JPX カレンダーを J-Quants から取得して market_calendar を更新する calendar_update_job を実装（バックフィル、健全性チェック含む）。

  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラス（pipeline.ETLResult）を定義し etl.py で再エクスポート。
    - 差分取得、保存（jquants_client を経由した idempotent 保存）、品質チェック（quality モジュール）を想定した設計方針とユーティリティ関数を実装。
    - テーブル存在チェック、最終日取得などの低レベルヘルパーを実装。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などを計算。
    - Value: PER（price / EPS）と ROE を raw_financials と prices_daily から計算（EPS が 0 / NULL の場合は None）。
    - DuckDB を用いた窓関数/集計で実装。データ不足時は None を返す設計。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: 任意ホライズン（デフォルト [1,5,21]）の fwd_* を LEAD() により一括算出。
    - IC（Information Coefficient）計算: factor と将来リターンのスピアマンランク相関（ランクは同順位平均ランクに対応）を実装。小サンプル時の保護（3件未満で None）。
    - 統計サマリー: count / mean / std / min / max / median を算出するユーティリティ。
    - 外部依存を持たず標準ライブラリと DuckDB のみで動作。

- パッケージエクスポート整理
  - research と ai の __init__ による関数再エクスポートを実装（例: kabusys.ai.score_news, kabusys.research.calc_momentum 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は明示的な ValueError を発生させることで意図せぬ公開や不正な呼び出しを防止。

Notes / 補足
- DuckDB のスキーマ（期待されるテーブル）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を前提とし、レスポンスパースに堅牢性対策（前後余計なテキストの切り出し等）を実装。
- ルックアヘッドバイアス防止のため、すべての時間窓／クエリで明示的に target_date を用いて過去データのみ参照する設計を採用。
- テストしやすさのため、OpenAI 呼び出しや sleep 等を差し替え可能な設計（モジュール内で差し替えやすい関数分割）を行っている。

今後の予定（例）
- ai のレスポンス検証・異常時の監査ログ整備強化
- ETL の具体的な差分取得ロジックと quality チェックの実装拡充
- ユニットテスト・統合テストの追加、CI 設定

--- 

この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートに合わせて適宜修正してください。