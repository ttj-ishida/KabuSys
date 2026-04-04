CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Note: この CHANGELOG は与えられたコードベースから推測して作成しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- 基本パッケージ初期実装
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル（プロジェクトルートの .env / .env.local）や OS 環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理など。
  - Settings クラスを提供。J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル / 環境（development / paper_trading / live）などを環境変数から取得・検証。
  - 必須値未設定時は ValueError を送出する _require ユーティリティ。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理、1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事／3000 文字でトリム。
    - リトライ戦略: 429（レート制限）・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション実装（JSON 抽出、results キー/型、既知コードのみ採用、数値検査、±1.0 でクリップ）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）により部分失敗時のデータ保護を実現。
    - score_news API を公開（conn, target_date, api_key を引数に取り、書き込み件数を返す）。APIキー未設定時は ValueError。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能に設計（_call_openai_api の注入/patch を想定）。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満（排他）データのみ使用し、ルックアヘッドバイアスを排除する設計。
    - マクロニュースはニュース NLP のウィンドウ計算を利用してタイトルを抽出し、OpenAI（gpt-4o-mini）でセンチメントを算出。記事がない場合は LLM 呼び出しをスキップして 0.0 を使用。
    - LLM 呼び出しはリトライ実装（RateLimit / 接続 / Timeout / 5xx を再試行）とフェイルセーフ（最終的に 0.0 にフォールバック）を備える。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB エラー時は ROLLBACK を試行して例外を伝播。

- データ基盤（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - market_calendar を基に営業日判定・前後営業日取得・期間内営業日取得・SQ判定を提供。
    - DB にデータがない場合は曜日ベースでフォールバック（土日を非営業日扱い）。
    - next_trading_day / prev_trading_day は DB 登録値を優先しつつ未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job を提供。J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェック含む）。

  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.py から再エクスポート）。ETL の実行結果・品質問題・エラー一覧を保持。
    - 差分更新・backfill、API 取得 → jquants_client 経由で冪等保存（ON CONFLICT 相当）・品質チェックを行う設計方針を実装（pipeline モジュールに基礎実装）。
    - デフォルトのバックフィルやカレンダー先読み等の定数を定義。
    - エラーと品質問題は収集して上位に伝える（Fail-Fast ではなく全件収集する動作を想定）。

  - jquants_client / quality などのクライアント群（参照実装を使用）と連携する設計。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算は prices_daily / raw_financials のみ参照し、実運用系 API へは接触しない安全な実装。
    - データ不足時には None を返す設計（堅牢性を重視）。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: target_date から指定ホライズン先のリターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）でファクター有効性を評価。記録不足時は None。
    - 統計サマリー（factor_summary）/ ランク変換ユーティリティ（rank）を提供。
    - pandas など外部依存を持たない純 Python 実装。

- 共通実装・設計上の注意点
  - DuckDB を想定した SQL 実行・日付取り扱い（date オブジェクト）を採用。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を内部ロジックで直接参照しない関数設計（外部から target_date を注入する方式）。
  - OpenAI 呼び出しや外部 API のフェイルセーフ: エラー時にスキップ／既定値で継続する方針（例外は適切に上位へ伝播する箇所のみ）。
  - テスト容易性を考慮し、OpenAI 呼び出しやファイル読み込み部を patch / 差し替え可能に実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 今後の改善候補（コードから推測）
- OpenAI API キー管理: より安全なシークレット管理（Vault 等）検討。
- 単体テスト・統合テストの拡充（外部 API のモックや DuckDB のテストフィクスチャ）。
- performance チューニング（DuckDB クエリのインデックス／パーティショニング、AI バッチサイズ最適化など）。
- ai スコアのリスク管理（コスト・レート制限対策、非同期処理の導入）。