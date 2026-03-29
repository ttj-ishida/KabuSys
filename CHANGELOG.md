# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-29

### 追加 (Added)
- パッケージ初期実装を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理モジュールを実装 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWDに依存しない）
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ等に対応）
  - 環境変数必須チェック用のヘルパー _require
  - Settings クラスを提供（プロパティ経由で設定取得）
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別: KABUSYS_ENV（development / paper_trading / live）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュースNLP（AI）モジュールを追加 (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して銘柄ごとのニュースを作成
  - OpenAI（gpt-4o-mini）JSON Mode を使用して銘柄別センチメントを取得
  - バッチ処理（1 API コールあたり最大 20 銘柄）
  - 1銘柄当たり最大記事数・最大文字数のトリム（デフォルト: 10記事・3000文字）
  - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）
  - レスポンスバリデーション（JSON 抽出、results 配列、code と score の検証、スコアの ±1.0 クリップ）
  - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト対策を考慮）
  - パブリック API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す
  - ユニットテスト用フック: _call_openai_api を patch で差し替え可能

- 市場レジーム判定モジュールを追加 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動）200日移動平均乖離（重み70%）と
    マクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）判定
  - マクロニュース選別はタイトルベースでキーワードフィルタ（複数キーワード定義）
  - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON 出力期待）
  - API リトライとフェイルセーフ: API 失敗時は macro_sentiment = 0.0 として継続
  - ルックアヘッドバイアス対策: target_date 未満のデータのみ使用、datetime.today() を参照しない設計
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
  - パブリック API: score_regime(conn, target_date, api_key=None) → 1 を返す（成功）

- Research（リサーチ）モジュールを追加 (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算
    - calc_value(conn, target_date): per, roe を raw_financials と prices_daily から計算
    - DuckDB の SQL＋ウィンドウ関数を活用した実装、データ不足時は None を返す
  - 特徴量探索・統計 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン計算（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算
    - rank(values): ランク付け（同順位は平均ランク）
    - factor_summary(records, columns): count/mean/std/min/max/median の集計
  - データ正規化ユーティリティは kabusys.data.stats.zscore_normalize を再利用してエクスポート

- データプラットフォーム関連モジュールを追加 (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの夜間更新ジョブ calendar_update_job(conn, lookahead_days=90)
      - J-Quants 経由で差分取得・冪等保存
      - バックフィル（直近 _BACKFILL_DAYS）および健全性チェック（未来日付の異常検出）
    - 営業日判定ユーティリティ
      - is_trading_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
      - is_sq_day(conn, d)
    - DB にカレンダーがない場合は曜日ベース（土日非営業日）でフォールバック
    - 最大探索範囲を定め無限ループを防止
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスと to_dict メソッド
    - 差分取得、保存（idempotent）、品質チェック（quality モジュールとの連携）を想定した設計
    - 最終取得日の取得ユーティリティ、テーブル存在チェック等の内部関数を提供
    - etl モジュールは ETLResult を公開（src/kabusys/data/etl.py）

- jquants_client, quality 等の外部インターフェースを想定した構成（モジュール依存注入・テスト容易性を考慮）

### 変更 (Changed)
- 初期リリースのため該当なし

### 修正 (Fixed)
- 初期リリースのため該当なし

### 削除 (Removed)
- 初期リリースのため該当なし

### セキュリティ (Security)
- 初期リリースのため該当なし

---

備考・設計上の重要点（ドキュメント的注記）
- ルックアヘッドバイアス防止:
  - AI 評価やファクター計算の多くの機能で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を受け取る設計になっている。
- フェイルセーフ:
  - OpenAI API 呼び出しが失敗した場合、例外を投げずにフェイルセーフ値（例: macro_sentiment=0.0）にフォールバックする設計を多く採用。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）はモジュールレベルで差し替え可能（unittest.mock.patch によるモックを想定）。
- DuckDB 互換性考慮:
  - executemany に空リスト渡せない等の制約を回避するチェックが含まれている。

今後の予定（非網羅）
- strategy / execution / monitoring モジュールの具体実装
- J-Quants / kabu ステーション向けクライアントの具体実装と統合テスト
- 追加の品質チェックルールおよび運用向け通知（Slack 等）の実装

---