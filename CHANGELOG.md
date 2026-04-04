CHANGELOG.md

すべての重要な変更点はこのファイルで管理します。フォーマットは "Keep a Changelog" 準拠です。

## [Unreleased]

なし

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 柔軟な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い）。
  - Settings クラスを公開（J-Quants, kabuステーション, LINE, DB パス, 監視閾値, ログレベル, 実行環境判定など）。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require 実装。
  - KABUSYS_ENV の許容値検証（development / paper_trading / live）および LOG_LEVEL 検証。

- AI/NLP モジュール (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数上限・文字数トリム制御。
    - OpenAI 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフ）。
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score 検査、スコアの ±1.0 クリップ）。
    - DuckDB 向けの安全な書き込み（部分成功時に既存スコアを保護するため、対象 code のみ DELETE → INSERT）。
    - テスト容易性を考慮して _call_openai_api を patch 可能に実装。

  - regime_detector:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily と raw_news を参照し、MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - OpenAI 呼び出しは独立実装。API エラー時は macro_sentiment=0.0 のフェイルセーフを採用。
    - OpenAI 呼び出しに対するリトライ（指数バックオフ）とステータスコードに応じた振る舞い。
    - 判定結果の閾値とスコアクリップ処理の実装。

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と夜間バッチ更新 job（jquants_client を利用して差分取得→冪等保存）。
    - 営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない日は曜日ベースのフォールバック（週末を非営業日扱い）。NULL 値の扱いに注意した実装。
    - 最大探索日数制限と健全性チェック（過度な未来日付のスキップ、バックフィル日数）。

  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラーの収集、to_dict による辞書化）。
    - 差分更新・バックフィル・品質チェックを含む ETL 設計方針の基礎実装（jquants_client / quality モジュール前提）。
    - DuckDB 互換性を考慮したユーティリティ（テーブル存在確認、最大日付取得の骨組み）。
    - data.etl モジュールで ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER/ROE）を DuckDB 上で計算する関数を提供（calc_momentum / calc_volatility / calc_value）。
    - データ不足時の None 処理、ログ出力、戻り値を (date, code) ベースの dict リストで返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns：任意ホライズン）、IC（calc_ic：Spearman ランク相関）、ランク変換、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージ初期化で主要関数を公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の設計上の注意・挙動
- AI モジュールは OpenAI API キーが必要（api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照）。未設定時は ValueError を送出します。
- OpenAI 呼び出しの失敗（レート制限・ネットワーク・タイムアウト・サーバーエラー）はリトライあるいはフェイルセーフ（0.0）にフォールバックし、処理を継続します。これにより ETL / スコア生成の可用性を高めていますが、API の連続障害時はスコアが 0 に偏る可能性があります。
- 各種スコアは所定範囲にクリップされます（ニューススコア ±1.0 等）。
- DB 書き込みは冪等化を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK ハンドリング）。部分失敗時は既存データ保護のため対象コードのみに対する削除を行います。
- ルックアヘッドバイアス防止のため、すべての時刻／日付ロジックは target_date ベースで動作し、datetime.today()/date.today() を直接参照しない設計です（ただし calendar_update_job だけは実運用向けに date.today() を使用）。
- DuckDB との互換性対応（executemany に空リストを渡さない等の対応）を行っています。

### マイグレーション / 利用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション）
  - OPENAI_API_KEY（AI スコアリング系を使用する場合）
  これらは settings 経由でアクセスできます（未設定時は ValueError）。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードはプロジェクトルートを基準に行われます。パッケージ配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部で _call_openai_api を定義しており、unittest.mock.patch による差し替え（モック化）を想定しています。
  - score_news / score_regime は api_key を引数で注入可能です。

---
（以上）