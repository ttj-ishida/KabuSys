# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。主な追加内容と設計上の要点を以下に示します。

### 追加 (Added)
- パッケージ初期公開
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - 外側から利用可能なモジュール群を __all__ で公開（data, research, ai, ...）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
  - プロジェクトルート検出は .git または pyproject.toml を基準に実行（CWDに依存しない）。
  - .env のパース機能を独自実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - 環境変数の保護（OS環境変数を protected として .env.local で上書き禁止にできる処理）。
  - Settings クラスを提供し、J-Quants・kabuAPI・LINE・DBパス・監視閾値・実行環境などの設定値取得をプロパティで提供。
  - 必須値未設定時は明示的に ValueError を投げる _require を実装。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証を行う。

- ニュースNLP（AI） (src/kabusys/ai/news_nlp.py / src/kabusys/ai/__init__.py)
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを算出して ai_scores テーブルへ保存する機能を実装。
  - 処理の流れ：対象ウィンドウ計算（JST基準） → 記事集約（銘柄ごとトリム・件数制限） → チャンク（最大20銘柄）でAPI呼び出し → レスポンスバリデーション → スコアクリップ → ai_scores に置換的書き込み（DELETE → INSERT）。
  - フェイルセーフ：API失敗時は個別チャンクをスキップし、全体の処理継続を担保。429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
  - レスポンスパースの堅牢化（JSON Modeでも余分なテキストが混ざるケースに対応して最外の {} を抽出）。
  - スコアの型検証、未知銘柄コードの無視、数値の有限性チェック、最大±1.0でクリップ。
  - 単体テスト容易性のため、OpenAI呼び出しを差し替え可能（内部 _call_openai_api）。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321（Nikkei 225 連動ETF）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等書き込み。
  - LLM呼び出しは gpt-4o-mini（JSON出力）を使用し、APIリトライ・エラー時は macro_sentiment=0.0 にフォールバックすることでフェイルセーフを実現。
  - ルックアヘッドバイアス対策：target_date 未満のみのデータを使用し、datetime.today() を参照しない設計。
  - 冪等性とトランザクション制御（BEGIN / DELETE / INSERT / COMMIT、例外時のROLLBACK）を実装。
  - 設定可能な定数（ウィンドウサイズ・重み・閾値・最大記事件数・モデル名・リトライ等）をモジュール定義で管理。

- 研究系（Research）ユーティリティ (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - calc_momentum：1M/3M/6M リターン、200日MA乖離の算出（prices_daily 参照）。
    - calc_volatility：20日 ATR、相対ATR、20日平均売買代金、出来高比率等の算出。
    - calc_value：raw_financials から直近財務を取得して PER / ROE を計算（欠損やゼロEPSに対応）。
    - 設計上、外部発注API等にはアクセスせず DuckDB 上で完結。
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns：複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算（結合は code ベース、3銘柄未満で None を返す）。
    - rank：同順位は平均ランクを返すランク関数（丸めで ties 判定の安定化）。
    - factor_summary：各カラムの count/mean/std/min/max/median を算出。
  - research パッケージで主要関数を再エクスポート。

- データ管理 (src/kabusys/data/*)
  - カレンダー管理 (calendar_management.py)
    - JPXマーケットカレンダーを扱うユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といったAPI）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を行う設計。
    - calendar_update_job：J-Quants API から差分取得して market_calendar に冪等保存。バックフィルと健全性チェック（未来日付の異常検出）を実装。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを定義し、フェッチ数・保存数・品質問題・エラーの集約を行う（to_dict を持つ）。
    - パイプライン設計に関するドキュメントに従い、差分更新・バックフィル・品質チェック・idempotent 保存を想定したインターフェースを整備。
    - jquants_client の fetch/save 関数を利用する前提で実装している（依存箇所を分離）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- 環境変数の読み込みで OS 環境変数を保護（.env.local 等による意図しない上書きを防止）。
- 必須トークン（OpenAI / J-Quants / Kabu API）の未設定時は明確なエラーを出すことで誤動作を抑止。

### 設計上の注記 / 既知の振る舞い
- ルックアヘッドバイアス防止：AI・リサーチ関連は内部で datetime.today() を参照せず、必ず呼び出し元が target_date を渡す設計。
- DuckDB 前提：各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて実行する設計。テーブルスキーマ・存在判定に依存するため、事前のスキーマ準備が必要。
- トランザクションと冪等性：DB 書き込みは可能な限り冪等化（DELETE→INSERT 等）し、例外発生時はROLLBACKを試行して上位へ伝播する。
- OpenAI 呼び出し：JSON Mode を利用し厳密な JSON 出力を期待するが、パース時の余分なテキストに対して回復処理も備える。
- テスト容易性：OpenAI 呼び出し関数や環境自動読み込みを差し替え可能にして単体テストを容易にしている。

### 互換性に関する注意（Breaking Changes）
- 初版リリースのため互換性関連の変更点はありません。

---

今後の改善候補（メモ）
- ai スコアの信頼性を高めるためのキャリブレーション/ヒューリスティック追加
- ETL の並列化・スループット改善
- エラーモニタリング・アラート連携の強化（LINE 通知等）
- docs/ に使用方法やテーブルスキーマ（DuckDB）のサンプルを追加

以上。必要であれば各モジュールごとの詳細な変更点や使用例を別途まとめます。