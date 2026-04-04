# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本エクスポートを定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0。

- 環境設定 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - OS 環境変数は保護され、.env/.env.local の上書きを防止可能。
  - .env パーサーの実装:
    - コメント行・空行を無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートをサポートし、バックスラッシュでのエスケープ処理に対応。
    - クォートなしの値では "#" がスペースまたはタブの直前にある場合にコメントと判断。
  - Settings クラスを提供（環境変数の型変換・デフォルト値・検証を含む）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル / 環境モード（development, paper_trading, live）等のプロパティ。
    - 必須環境変数未設定時は ValueError を送出するヘルパーを提供。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp):
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI (gpt-4o-mini, JSON mode) へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: JST 前日 15:00 〜 当日 08:30（UTC に変換して DB との比較を行う）。
    - バッチサイズ: 最大 20 銘柄/リクエスト。銘柄あたり最大 10 記事、最大 3000 文字でトリム。
    - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出、"results" リスト形式、各要素に code と score を期待。未知コードは無視、スコアは ±1.0 にクリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さない等の注意点を実装。
    - テスト容易性: OpenAI 呼び出し箇所はモック差し替え可能（関数を分離）。
    - 最終的に ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
  - 市場レジーム判定 (regime_detector):
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次で market_regime を判定。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI により -1.0〜1.0 のスコアを取得。
    - スコア合成後クリップし、閾値により label を bull/neutral/bear に分類。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行して例外を伝播。
    - OpenAI 呼び出しの失敗や JSON パース失敗は macro_sentiment=0.0 でフェイルセーフ継続。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management):
    - market_calendar テーブルの取得・差分更新ジョブ（J-Quants から差分取得し冪等に保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ回避。
    - バックフィル／健全性チェックを実装（過度に未来の日付はスキップ）。
  - ETL パイプライン (pipeline / etl):
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーなどを集約）。
    - 差分更新、backfill、品質チェック（quality モジュール呼び出し予定）、J-Quants クライアント経由の冪等保存を想定した設計。
    - デフォルトバックフィル日数・カレンダー先読み等の定数を提供。
    - data.etl から ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - ファクター計算 (factor_research):
    - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。データ不足時は None。
    - ボラティリティ／流動性: 20 日 ATR（true_range 制御）、ATR/終値比、20 日平均売買代金・出来高変化率。必要行数が満たない場合は None。
    - バリュー: raw_financials の直近財務データと当日の株価から PER・ROE を計算（EPS 無効時は None）。
    - 全て DuckDB を用いた SQL 実装。外部 API/発注は行わない。
  - 特徴量探索 (feature_exploration):
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）までのリターンを LEAD を使って一括取得。horizons の妥当性チェックあり。
    - IC 計算 (calc_ic): Spearman ランク相関を実装（同順位は平均ランク処理）。有効レコードが 3 未満なら None。
    - ランク変換ユーティリティ (rank) は同順位処理（丸め対策）を考慮。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。None を除外。

### 変更 (Changed)
- 初回リリースのため変更履歴は特になし（ベース実装の追加）。

### 修正 (Fixed)
- 初回リリースのため修正履歴は特になし。

### 設計・品質上の注記
- ルックアヘッドバイアス対策: 各モジュール（news, regime, research 等）は内部で datetime.today()/date.today() を直接参照せず、target_date を引数で受け取る設計。
- OpenAI 呼び出しはテストしやすいように関数分離（ユニットテストでモック置換可能）。
- DuckDB の互換性（executemany の空リスト制約等）を考慮した実装。
- DB 書き込みは可能な限り冪等化（DELETE → INSERT、ON CONFLICT を想定）を行い、部分失敗時の既存データ保護を意識。

---

今後の予定（例）
- strategy / execution / monitoring の具象実装追加（本バージョンではパッケージエントリのみ）。
- 品質チェックモジュールの具体実装と ETL パイプラインの統合テスト。
- OpenAI レスポンスハンドリングの強化（プロンプト改善、より堅牢な JSON 抽出ロジック）。
- 性能改善（大規模データ処理における DuckDB クエリ最適化、並列処理など）。

（必要であれば、各モジュールごとにより詳細な変更点や実装上の注意点を追記します。）