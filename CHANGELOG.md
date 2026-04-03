# Changelog

すべての変更は「Keep a Changelog」形式に従い、Semantic Versioning に準拠します。  

注: 本 CHANGELOG はリポジトリ内のソースコードを元に推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に合わせて調整してください。

## [0.1.0] - 2026-04-03

### Added
- パッケージ初期リリース。パッケージ名: kabusys, バージョン: 0.1.0。
  - src/kabusys/__init__.py にて public API を export（data, research, ai, execution, monitoring, strategy 等のサブパッケージ想定）。
- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイル自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - .env パーサが export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（スペース直前の#のみ）等に対応。
  - 上書き時に OS 環境変数を保護する protected 機構を実装。
  - Settings クラスを提供し、主要な設定をプロパティとして公開（J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / 環境種別・ログレベル検証など）。
  - 必須環境変数未設定時には明示的な ValueError を送出する _require ユーティリティを実装。
- AI（自然言語処理）関連機能を追加（src/kabusys/ai）。
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信しセンチメントスコアを ai_scores テーブルへ書き込む機能。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数の上限トリム、レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証）、スコア ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフ & リトライ。
    - 失敗時は例外伝播せずにログを残して個別チャンクをスキップ（フェイルセーフ）。
    - calc_news_window により日本時間ベースのニュース収集ウィンドウを UTC naive datetime で返す実装。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはマクロキーワードでフィルタし OpenAI でスコアリング（JSON 出力期待）し、スコアは -1..1 にクリップ。
    - API エラー時は macro_sentiment=0.0 にフォールバック。
    - 計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込む。
  - 共通:
    - OpenAI クライアント呼び出し箇所はテスト容易性のため個別の _call_openai_api を経由（unittest.mock で差替可能）。
    - OPENAI_API_KEY が未設定の場合は ValueError を送出する明確な挙動。
- Data モジュールを追加（src/kabusys/data）。
  - calendar_management モジュール（市場カレンダー管理）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを提供。
    - market_calendar テーブルが存在しない場合は曜日（土日）ベースのフォールバックを行う一貫した挙動。
    - calendar_update_job により J-Quants API（jquants_client を経由）から差分取得して market_calendar を更新（バックフィルや健全性チェックを実装）。
    - DB 登録値優先、未登録日は曜日フォールバックという設計で DB がまばらな場合でも整合性を保つ。
  - pipeline / etl / quality 周りの基盤
    - ETLResult データクラス（src/kabusys/data/pipeline.py）を追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約可能に。
    - ETL の差分更新・バックフィル・品質チェック方針を実装するための下地（jquants_client / quality との連携を想定）。
    - data/etl は ETLResult を再エクスポートする簡易インターフェースを提供。
- Research モジュールを追加（src/kabusys/research）。
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）を計算する関数を提供。
    - DuckDB 上で SQL と Python を組み合わせて高速に計算。欠損データやデータ不足時の None ハンドリングを設計。
    - 出力は date, code を含む辞書リスト。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず純 Python 実装（pandas 等なし）。
  - research/__init__.py で主要 API を再エクスポート（zscore_normalize のようなユーティリティを data.stats からも利用）。

### Changed
- （なし：初回リリース）

### Fixed
- （なし：初回リリース）

### Notable design / 実装上の注意点（ドキュメント的補足）
- ルックアヘッドバイアス防止:
  - AI モジュール、研究モジュール共に date.today() や datetime.today() を参照しない。全ての関数は target_date を外部から受け取り、DB クエリは target_date より前／LEAD/LEAD を適切に扱っている。
- DB 書き込みは冪等性を考慮:
  - market_regime / ai_scores 等への書き込みは削除→挿入または executemany を使い、部分失敗時に既存データを不必要に消さない設計。
- OpenAI 呼び出し:
  - JSON Mode（response_format={"type": "json_object"}）を利用する想定。レスポンスパースに失敗した場合はロギングしてフォールバック（またはスキップ）する。
  - リトライは 429 / ネットワーク断 / タイムアウト / Server 5xx を対象に指数バックオフ。非 5xx の API エラーはリトライしない方針（一部モジュールで差異あり）。
- .env パーサ/自動ロード:
  - .env の Quoted 値でのバックスラッシュエスケープ処理や export KEY=val 形式へ対応。
  - 自動ロード前にプロジェクトルートを探索（パッケージ配布後の CWD 非依存）。
  - OS 環境変数は protected として上書き防止（.env.local は override=True でも protected を尊重）。
- エラーハンドリング:
  - AI / ETL / カレンダー取得など外部依存処理は基本的に例外を抑止してログに残す（部分失敗を許容）、ただし DB 書き込みなど致命的な箇所は適切に ROLLBACK を試みた上で例外を再送出する。
- 時刻管理:
  - ニュースウィンドウは日本時間（JST）を元に UTC naive datetime に変換して DB（UTC 想定）と照合する実装。

### Environment / 必要な環境変数（主なもの）
- OPENAI_API_KEY: OpenAI を利用する機能（news_nlp, regime_detector）で必須（関数呼び出し時に引数で上書き可能）。
- JQUANTS_REFRESH_TOKEN: J-Quants API を利用する ETL/カレンダー周りで必須。
- KABU_API_PASSWORD / KABU_API_BASE_URL: kabu ステーション API 関連設定。
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（オプション）。
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等: デフォルトパスが設定されている（data/ 以下）。
- KABUSYS_ENV: development / paper_trading / live のいずれか（検証あり）。
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。

### Developers
- テスト容易性のため、OpenAI 呼び出し箇所は _call_openai_api を外出ししており、unittest.mock.patch で差し替え可能。
- DuckDB のバージョン差異（executemany の空リストや配列バインドの挙動）を考慮した実装になっている。

---

今後のリリースでは以下を含めると良い提案:
- リリース毎に変更内容（追加 API/破壊的変更/バグ修正）をコミット単位で明確化。
- jquants_client / quality / monitoring / execution など未掲載のモジュールについての詳細な挙動と既知の制約を追記。