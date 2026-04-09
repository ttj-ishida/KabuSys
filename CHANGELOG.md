# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0 (初期リリース)

## [Unreleased]
- なし

## [0.1.0] - 2026-04-09
初回公開リリース。日本株自動売買 / 研究用パイプラインの基本コンポーネントを実装しました。主要な追加点は以下の通りです。

### 追加
- パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージ公開対象モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` に定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env 自動読み込み機能（プロジェクトルート探索: `.git` または `pyproject.toml` を基準）。
  - .env のパース機能強化：
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
  - 読み込み優先順位: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 環境変数保護機能（OS 環境変数は protected として上書き抑制）。
  - `Settings` クラスを提供し、以下の設定をプロパティで取得可能:
    - J-Quants / kabuステーション / LINE API / DB パス（DuckDB / SQLite）/ Paper Trading 設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）/ 監視関連（PID ファイル・KILL フラグ・リソース閾値）/ 環境モード（development/paper_trading/live）/ ログレベル
  - 値検証を実装（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の妥当性チェック）。
  - 必須環境変数未設定時は明確な例外メッセージを送出する `_require`。

- データ処理（Data Platform）
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーを扱う `market_calendar` に対する読み書き・判定関数を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 `calendar_update_job` を実装（J-Quants クライアント経由で差分取得・バックフィル・健全性チェック）。
    - 最大探索日数やバックフィル、未来日チェックなどの安全策を導入。
  - ETL / パイプライン (`kabusys.data.pipeline`, `kabusys.data.etl`)
    - ETL 実行結果を表す `ETLResult` dataclass を公開（取得数・保存数・品質問題・エラー収集など）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携想定）を行う設計。
    - jquants_client の save_* 関数を使った冪等保存（ON CONFLICT 相当）を想定。

- AI 関連（ニュース NLP / レジーム判定）
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - 時間ウィンドウ（JST: 前日15:00〜当日08:30、UTC に変換）を厳密に計算する `calc_news_window`。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数/文字数制限（トリム）を実装。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーション／抽出 (`_validate_and_extract`) を実装。
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - DuckDB に対する書込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - テスト容易性のため `_call_openai_api` を patch 可能に設計。
    - 公開 API: `score_news(conn, target_date, api_key=None) -> int`（書き込んだ銘柄数を返す）。
  - レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（llm センチメント、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロ記事抽出（キーワードリスト） → OpenAI で JSON 出力を受け取りパース、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームはスコア合成後クリップし、閾値判定でラベル付与。結果を `market_regime` テーブルへ冪等書き込み。
    - 公開 API: `score_regime(conn, target_date, api_key=None) -> int`。

- リサーチ（因子・特徴量） (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日MA乖離（ma200_dev）を DuckDB SQL で計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials（最新レコード）と当日の株価から PER / ROE を計算。
    - 入力は prices_daily / raw_financials のみ。結果は (date, code) をキーにした dict リストで返す。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを算出。複数ホライズンをまとめて高速取得。
    - calc_ic: Spearman（ランク相関）に基づく IC 計算。None/不足データは除外、最小件数チェック。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
    - rank: 平均ランク（同順位は平均ランク）を算出（丸め処理で ties の誤差を軽減）。
  - zscore_normalize は data.stats から再エクスポート。

### 改善・設計上の注意点（重要）
- ルックアヘッドバイアス防止のため、いずれのモジュールも内部で datetime.today()/date.today() を直接参照しないよう設計（必要な基準日は引数で注入）。
- DuckDB に関する実装上の注意:
  - executemany に空リストを渡さない（互換性のため事前チェック）。
  - 一貫した BEGIN / DELETE / INSERT / COMMIT の冪等書き込みパターンを採用。
- OpenAI 呼び出しは堅牢なリトライとレスポンス検証を行い、API 側の異常時でもシステム全体が停止しないフェイルセーフを採用。
- テスト容易性に配慮して API 呼び出し箇所はパッチで差し替え可能に実装。

### 修正
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### セキュリティ
- 環境変数や API キー（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を取り扱うため、設定ロードに保護（protected keys）を導入。自動読み込みを無効化するフラグを提供。

---

この CHANGELOG はコードベースからの推測に基づき作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、各機能ごとにより詳しい変更点（関数単位の API 仕様、例外/戻り値の詳細、既知の制限や TODO）を追記します。