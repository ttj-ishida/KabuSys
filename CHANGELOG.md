# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

※コードベースから推測して作成しています。実際のリリースノートと差異がある場合があります。

## [0.1.0] - 2026-03-28
初回リリース。日本株向けのデータプラットフォーム、リサーチ、AI ベースのニュース解析・市場レジーム判定、および運用ユーティリティ群をまとめた初期実装を追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。サブモジュールを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定 / config
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境（KABUSYS_ENV, LOG_LEVEL）などをプロパティ経由で取得。
  - 環境変数必須チェックで未設定時に明確なエラーメッセージを発生させる _require を実装。
- データプラットフォーム（data）
  - ETL パイプライン用の結果型 ETLResult をデータクラスで実装（品質チェック結果・エラー集約を含む）。
  - pipeline: 差分取得、バックフィル、品質チェック設計に沿ったユーティリティ群を実装（jquants_client / quality を利用する設計）。
  - calendar_management:
    - 市場カレンダーの管理・判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job を追加し、J-Quants から差分取得 → 保存する夜間ジョブの仕様を実装。
    - DBにデータがない場合の曜日ベースフォールバックや最大探索日数などの安全措置を実装。
  - ETL / calendar 周りは DuckDB を利用する前提で設計。
- リサーチ（research）
  - factor_research:
    - Momentum, Volatility, Value, Liquidity 等の定量ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MAが不足する場合は None を返す）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（欠損ハンドリングあり）
      - calc_value: PER, ROE（raw_financials の最新レコードを target_date 以前から取得）
    - DuckDB 上のウィンドウ関数 / 集計で記述し、外部 API への依存を排除。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで取得（ホライズンの検証あり）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（レコード不足時は None）。
    - rank: 同順位は平均ランクで処理するランク変換ユーティリティ（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
- AI（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を生成。
    - バッチサイズ、記事数上限、文字数トリム等のトークン対策を実装。
    - JSON Mode を前提とした応答パースと堅牢なバリデーション実装（余分な前後テキスト復元ロジック含む）。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。リトライ失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - ai_scores テーブルへは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を確保。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース（LLM）センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp の時間窓関数 calc_news_window を利用して取得。マクロキーワードによるフィルタ実装。
    - OpenAI 呼び出し用に専用実装を持ち、レスポンスパース失敗や API エラー時は macro_sentiment=0.0 へフォールバック（フェイルセーフ）。
    - 再試行ロジック・指数バックオフ・最大リトライ・5xx の扱いを実装。
- その他実装上の配慮
  - すべての「日付基準」処理は datetime.today() / date.today() の直接参照を避け、外部からの target_date パラメータに依存する設計（ルックアヘッドバイアス防止）。
  - DuckDB のバインド挙動（executemany に空リスト不可等）や型差異に対するワークアラウンドを実装。
  - ロギング（logger）を各モジュールで利用し、警告や情報を適切に出力するように設計。

### Security
- 環境変数に依存する機密情報:
  - OPENAI_API_KEY（LLM 呼び出し）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知）
- .env 自動ロードはプロジェクトルート検出に基づく。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- API キー未設定時は明示的な ValueError を発生させる箇所があるため、運用時は環境変数の管理に注意。

### Notes / Known limitations
- jquants_client の具体実装はこのスコープには含まれない（外部クライアントに依存する設計）。ETL / calendar_update_job は jquants_client の fetch/save を呼び出す設計。
- news_nlp/regime_detector は gpt-4o-mini を前提にプロンプトと JSON Mode を利用する実装。モデル仕様変更や API 仕様変更によりパース/バリデーションロジックの調整が必要になる可能性あり。
- 一部の関数は DuckDB 固有の挙動（日付型・executemany の振る舞い）に依存しており、DB バージョンにより挙動差が出る場合がある。既知の互換性対策はコード内にコメントとして記載。
- 現フェーズでは PBR や配当利回り等のバリューファクターは未実装（calc_value 説明に記載）。

### Deprecated
- なし

### Fixed
- 初回リリースのため該当なし

### Removed
- なし

---

今後のリリースでは、ドキュメントの充実（API 使用例、運用手順）、追加ファクター・リサーチ指標、OpenAI 呼び出しの抽象化とテスト用モック強化、kabu ステーションとの連携機能（発注ロジックなど）の追加が想定されます。