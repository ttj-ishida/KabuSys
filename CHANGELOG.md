Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる追加機能・設計方針・注意点を反映しています。

---
# CHANGELOG

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

v0.1.0（初回リリース）
---------------------

リリース日: 2026-04-04（推定）

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化 (src/kabusys/__init__.py) を追加。バージョンを "0.1.0" として公開し、主要サブパッケージを __all__ でエクスポート。
- 環境・設定管理
  - src/kabusys/config.py
    - .env / .env.local 自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
    - .env パーサを実装：コメント・export プレフィックス・クォートとバックスラッシュエスケープ対応。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - OS 環境変数を保護する読み込みロジック（.env.local は上書き、protected set で保護）。
    - 必須環境変数取得関数 _require、Settings クラスを実装。J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境（development/paper_trading/live）・ログレベル検証等のプロパティを提供。
- AI（NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0～1.0）を算出。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたりの最大記事数・文字数トリム、429/ネットワーク/5xx に対する指数バックオフ再試行、レスポンスバリデーション（JSON整形・results配列・code/score検証）を実装。
    - DuckDB への書き込みは部分置換（該当 code の DELETE → INSERT）で冪等性と部分失敗時の保護を確保。
    - calc_news_window 関数：JST基準（前日15:00～当日08:30）を UTC naive datetime に変換するユーティリティを実装。
    - テスト容易性のため _call_openai_api が差し替え可能（patch 用）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロキーワードで raw_news をフィルタし、OpenAI 呼出しはリトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - レジーム結果は market_regime テーブルへ冪等的にトランザクション（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - lookahead バイアス回避のため、target_date 未満のデータのみ参照する設計。
- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム (1M/3M/6M リターン)、200日MA乖離、ATR（20日）ベースのボラティリティ／流動性指標、バリュー（PER/ROE）を prices_daily / raw_financials を元に計算する関数群（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の扱い（不足なら None）、戻り値は (date, code) を含む dict のリスト。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず、標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- Data（カレンダー・ETL）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理：market_calendar テーブルを基に is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB データがない場合は曜日ベース（平日営業）でフォールバック。最大探索日数制限で無限ループ防止。
    - calendar_update_job：J-Quants API（jquants_client 経由）からの差分取得・バックフィル（直近 _BACKFILL_DAYS を再取得）・保存処理を実装（健全性チェック含む）。
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを導入（ETL の取得数・保存数・品質問題・エラーの集約）。
    - ETL の差分取得・backfill・保存・品質チェックの設計方針をコードで反映（jquants_client / quality モジュールと連携）。
    - DuckDB のテーブル存在確認等ユーティリティを実装。
  - src/kabusys/data/etl.py で ETLResult を公開再エクスポート。
- その他
  - OpenAI クライアント呼び出し部は明示的にパッチ差替え可能に実装（テストしやすさに配慮）。
  - 各モジュールで詳細なログ出力を追加（INFO/WARNING/DEBUG）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数の読み込みでは OS 環境変数を保護（.env で既存の OS 環境変数を不用意に上書きしない）する挙動を採用。
- OpenAI API キーの未設定時は ValueError を投げて明示的に通知（news_nlp.score_news / regime_detector.score_regime）。

注記・設計上の重要なポイント
- lookahead バイアス防止:
  - AI モジュール・リサーチ関数はいずれも内部で datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date 未満や window の排他条件を使用して先読みを防止。
- OpenAI 連携:
  - モデルは gpt-4o-mini を想定。JSON mode（response_format={"type":"json_object"}）を使用。
  - レスポンスの不完全性（前後余計なテキスト等）に対する頑健性（最外の {} 抽出等）を実装。
  - 再試行ポリシー（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を導入。
- DuckDB 依存:
  - 主要なデータ処理は DuckDB 接続を前提に SQL と Python を組合せて実装。
  - executemany の空リスト制約（DuckDB 0.10 の挙動）に対する回避コードあり（書き込み前に空チェック）。
- 可観測性:
  - 各処理で詳細なログ（Info/Warning/Debug）を出力するよう設計。
- テスト容易性:
  - OpenAI 呼出しの内部関数はモジュール内で差し替え可能に実装（unittest.mock.patch 推奨）。

既知の制約・注意点
- OpenAI API キーが必須（引数または環境変数 OPENAI_API_KEY）。未設定時は明示的にエラーになる。
- .env の自動読み込みはプロジェクトルートが検出できない場合スキップされる（配布後の動作を安全に保つため）。
- 一部の DB 書き込みは冪等化のため DELETE→INSERT を採用しているため、ETL の部分的失敗時でも既存データの保護に配慮しているが、完全なトランザクション分離は DB 側の仕様に依存する。
- News の時間ウィンドウ定義は JST ベース（前日 15:00 ～ 当日 08:30 JST）であり、内部比較は UTC naive datetime を用いる。

今後の予定（例）
- 外部サービス呼び出しのモック化や単体テストの充実。
- スコアリングの品質改善（プロンプトの改善、モデル選択の汎用化）。
- ETL の並列化やパフォーマンス改善、品質チェックの拡張。

---

Unreleased
---------
（空）

---

必要であれば、各関数／モジュールごとの変更例や利用方法、影響範囲の詳細（例: DB スキーマ期待値、.env.example に必要なキー一覧）を追記します。どのレベルの詳細を追記しますか？