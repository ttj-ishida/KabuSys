CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
本ファイルはコードベースの内容から推測して作成した初期リリース履歴です。

フォーマット:
- 変更は "Added", "Changed", "Fixed", "Security" などに分類しています。
- 日付はこのコード解析時点の推定リリース日を使用しています（推定: 2026-03-27）。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース。モジュール群を実装。
  - kabusys.config
    - .env ファイルと環境変数の自動読み込み機能を実装。
      - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
      - export KEY=val 形式、クォートとエスケープ、インラインコメントのパースに対応。
      - 環境変数保護（既存 OS 環境変数を protected として扱う）に対応。
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得）。
    - 必須変数未設定時は ValueError を送出する _require メソッドを実装。
    - 有効な環境値・ログレベルのバリデーションを実装（development/paper_trading/live 等）。

  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む score_news 関数を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算機能を実装。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、1 銘柄あたりの記事数・文字数トリム、JSON Mode レスポンスのバリデーションを実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実行。
    - レスポンス検証：JSON パースの復元ロジック、results 配列・code/score 検証、スコアの ±1 クリップ。
    - 部分失敗に備え、書き込みは「該当コードのみ DELETE → INSERT」で原子性と既存データ保護を確保。
    - テスト容易性のため _call_openai_api を patch 可能に設計。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - マクロ記事抽出（キーワードフィルタ）、OpenAI 呼び出し、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - MA 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

  - kabusys.data
    - calendar_management
      - JPX カレンダーの管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
      - market_calendar が未取得の場合は曜日ベース（土日）でフォールバックする一貫したロジックを実装。
      - calendar_update_job により J-Quants からの差分取得と冪等保存の夜間バッチ処理を実装（バックフィル・健全性チェックを含む）。
    - pipeline / etl
      - ETLResult データクラスを導入して ETL の実行結果（取得数・保存数・品質問題・エラー）を表現可能に。
      - 差分取得・バックフィル・品質チェックの設計（品質問題は収集して呼び出し元で判断）に沿った ETL 処理フレームワークの基礎を実装。
    - jquants_client と連携する設計（fetch/save の呼び出しを想定）。

  - kabusys.research
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日移動平均乖離）を prices_daily から計算。
      - calc_volatility: 20 日 ATR、相対ATR、20日平均売買代金・出来高比率を計算。
      - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。
      - いずれも DuckDB SQL を用いた実装で、データ不足時は None を返す安全設計。
    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンのランク相関（IC）を実装（None を適切に扱い、有効レコード数が 3 未満なら None を返す）。
      - rank: 同順位は平均ランクにするランク変換を実装（丸め処理で ties の安定化を図る）。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数を実装。
    - 研究向け関数群をエクスポートして再利用可能に。

  - 共通インフラ
    - DuckDB を主要データバックエンドとして利用。
    - OpenAI（gpt-4o-mini）を JSON Mode で利用する設計。
    - ロガー（logging）を利用した詳細な実行ログ・警告ログを適宜出力。
    - ルックアヘッドバイアス排除のため datetime.today()/date.today() を直接参照しない設計方針を各 AI/研究モジュールで徹底。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

Security
- 環境変数の取り扱いおよび必須キー未設定時の明示的エラーにより、誤設定による誤動作を防止する設計を採用。
- 外部 API キー（OPENAI_API_KEY 等）は明示的に要求し、関数引数で注入可能にしてテスト時の安全性を考慮。

Notes / Known limitations
- OpenAI 連携は外部サービスに依存するためネットワーク・料金・レート制限等に影響を受ける。API 呼び出し時は冪等性とフェイルセーフ（スコア 0.0 へのフォールバック）を確保している。
- ai_scores の書き込みは部分失敗を防ぐため、取得済みコードのみを対象に DELETE → INSERT を実施する。DuckDB バージョン差による executemany の制約に対処済み。
- calendar_update_job は J-Quants クライアント（jquants_client）実装に依存する。fetch/save が例外を投げた場合は安全にエラー処理して 0 を返す。
- 一部関数はプロジェクト固有（例: ETF 1321 を用いたレジーム判定）にハードコーディングされている点に注意。

開発・テストに関する補足
- テスト容易性のため、OpenAI 呼び出し部分はモック差し替え（unittest.mock.patch）を想定して実装されている（_call_openai_api を patch）。
- 環境読み込みロジックは __file__ を起点にプロジェクトルートを探索するため、CWD に依存しない設計。

今後の予定（例）
- ai スコア・レジーム判定のチューニング（プロンプト改善、モデル選択の柔軟化）
- ETL のエラーハンドリング強化と監視（監査ログ、メトリクス収集）
- Research モジュールの高速化（並列化、キャッシュ）および追加ファクターの実装
- J-Quants / kabu API クライアントの詳細実装・テストカバレッジ拡充

-------------------
（注）本 CHANGELOG は提供されたソースコードからの推測に基づき作成しています。実際のリリースノートやバージョン履歴が存在する場合はそちらを優先してください。