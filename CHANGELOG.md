# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージの初期リリースを追加。
  - パッケージメタ: kabusys v0.1.0（src/kabusys/__init__.py）。
  - 公開モジュールのトップレベル参照: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（kabusys.config）を導入。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサはコメント・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープに対応。
  - 読み込み時の上書き制御（override）と OS 環境変数を保護する protected キー機能を実装。
  - 必須環境変数チェック用ヘルパー _require を提供。
  - 設定プロパティをまとめた Settings クラスを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境判定など）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値検査を実装。

- ニュース NLP と市場レジーム判定（kabusys.ai）を追加。
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを計算。
    - チャンク処理（デフォルト 20 銘柄／回）、1 銘柄あたり記事数上限／文字数上限、JSON Mode を利用した応答バリデーションを実装。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時は個別チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なパース処理（前後余分テキストから最外側の {} を抽出する処理等）とスコアの ±1.0 クリップ。
    - 成功した銘柄のみ ai_scores テーブルへ置換（DELETE→INSERT）することで部分失敗時に既存データを保護。
    - 時間ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window で提供。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）200 日移動平均乖離 (ma200_ratio)（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からのデータ取得は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロキーワードで raw_news をフィルタし、OpenAI でマクロセンチメントを評価（記事がない場合は LLM 呼び出しを行わず macro_sentiment = 0.0）。
    - OpenAI 呼び出しを独立実装し、API エラーやパース失敗時は macro_sentiment を 0.0 にフォールバック。
    - レジーム判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試行。

- データ基盤ユーティリティ（kabusys.data）を追加。
  - calendar_management:
    - JPX カレンダーの管理ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar の有無に応じて DB 値優先・未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（取得・保存数、品質チェック結果、エラーの集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を行う設計。
    - エラー処理: 品質問題は収集して呼び出し元に報告（Fail-Fast ではない）。DB 存入処理は冪等を意識。

- 研究用モジュール（kabusys.research）を追加。
  - ファクター計算（factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None。
    - calc_value: raw_financials と当日の株価を組み合わせて PER, ROE を算出（EPS が 0 / NULL の場合 PER は None）。
    - すべて DuckDB に対する SQL 実行で実装、外部 API を呼ばない。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括取得（LEAD を使用）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。十分なサンプルがない場合は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化を行う）。
    - 実装は標準ライブラリ + DuckDB に依存し、pandas 等には依存しない設計。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動読み込みにおいて OS 環境変数を上書きしない既定挙動を採用し、.env の内容が誤ってシステム環境を上書きしないよう配慮。
- .env 読み込み失敗時は警告を出力して処理を継続（クラッシュしない）。

---

注意:
- OpenAI（gpt-4o-mini）へのアクセスを行う機能は API キー（引数 / 環境変数 OPENAI_API_KEY）が必須です。未設定時は ValueError を送出します。
- DuckDB を前提とした実装です（関数は DuckDB 接続オブジェクトを受け取る）。
- ロギングを随所で行い、API エラーやデータ不足時はフェイルセーフ（省略・0.0・None にフォールバック）で継続する設計になっています。

今後のリリースでは、strategy / execution / monitoring モジュールの実装拡張やテストカバレッジ強化、外部クライアントラッパーの抽象化などを予定してください。