# Changelog

すべての重要な変更履歴をここに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

最新の修正は上に記載しています。

## [Unreleased]

- （現在未リリースの変更はありません）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。主要な機能・モジュールと設計上の重要な振る舞いは以下のとおりです。

### 追加 (Added)

- パッケージ基盤
  - パッケージのエントリポイントを実装（src/kabusys/__init__.py）。
  - バージョン情報: 0.1.0。
  - 公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ に含まれる意図）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない）。
  - 読み込み順序: OS環境変数 > .env.local > .env。既存の OS 環境変数は保護される（protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用）。
  - .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理を考慮）。
  - Settings クラス実装（プロパティによる遅延評価）:
    - J-Quants / kabu-station / Slack / DB パス等の必須/デフォルト値取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証。
    - duckdb/sqlite のパス展開（Path.expanduser を利用）。

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - news_nlp.score_news
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチサイズ・トリム（記事数最大/文字数上限）・JSON Mode 応答の検証実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。非リトライエラーはスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗に備え、該当コードのみ DELETE → INSERT することで既存スコア保護。
    - calc_news_window ユーティリティ（JST基準のニュースウィンドウ計算）を提供。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して、市場レジーム（bull/neutral/bear）を算出。
    - マクロキーワードによる raw_news 抽出、OpenAI への JSON Mode 呼び出し、リトライ/フェイルセーフ動作実装。
    - 市場レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは news_nlp と独立したプライベート実装とし、モジュール結合を回避。

- リサーチ・ファクター計算 (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の計算（prices_daily 利用）。データ不足時の挙動を明確化。
    - calc_volatility: 20日 ATR、ATR比率、平均売買代金、出来高比率の計算（prices_daily 利用）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算。最新財務レコードの取得ロジックを実装。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターン計算（LEAD を利用）。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank, factor_summary: ランク付けと統計サマリー（count/mean/std/min/max/median）を提供。
  - いずれも DuckDB 接続を受け取り SQL と Python の組み合わせで実装。外部APIや pandas には依存しない設計。

- データプラットフォーム / ETL / カレンダー (src/kabusys/data)
  - calendar_management:
    - market_calendar を使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - calendar_update_job により J-Quants API からの差分取得と冪等保存をサポート（jq: jquants_client を介して fetch/save）。
    - カレンダーデータ未取得時は曜日ベースのフォールバック（平日＝営業日）を適用。検索最大レンジ制限で無限ループを防止。
  - pipeline / ETL:
    - ETLResult データクラス実装（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した骨組みを実装。
    - DB 上の最大日付取得などのユーティリティを提供。
  - etl モジュールは ETLResult を再エクスポート。

### 変更 (Changed)

- （初回リリースのため過去からの変更はありません）

### 修正 (Fixed)

- LLM / API 呼び出し周りの堅牢性強化
  - JSON 解析エラーや不正レスポンス時に例外を上位へ伝播させずフォールバック（0.0 またはスキップ）することで、ETL やレジーム判定の継続性を確保。
  - OpenAI API の APIError について status_code の有無に配慮した処理を実装（互換性を確保）。

### セキュリティ (Security)

- 環境変数の必須チェック（_require）により、APIキー未設定時に早期に検出して明示的なエラーを発生させる。

### 既知の制約 / 注意点 (Notes)

- OpenAI クライアントは openai パッケージに依存し、gpt-4o-mini モデルの JSON Mode を前提としたプロンプト設計を行っています。API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用して解決されます。
- DuckDB をデータ層に使用。executemany で空リストを渡せない制約（DuckDB 0.10 の挙動）を回避するため、書き込み前に空チェックを行っています。
- 日時の取り扱いはすべて日付/naive datetime（UTC 前提の保存等）で統一し、datetime.today()/date.today() を関数内部で乱用しない設計（ルックアヘッドバイアス対策）。
- .env パーサは多くのケースに対応していますが、極端に特殊なフォーマット（複雑なシェル式評価等）は想定外です。
- J-Quants / kabu-station / Slack など外部連携用のクライアント実装は jquants_client や外部モジュールを想定しており、本リリースではそれらの具体実装は別モジュールとなります。

---

メンテナンスやバグ修正・機能追加は今後のリリースで随時追記します。必要であれば、特定モジュールごとに詳細なリリースノートを分けて作成します。