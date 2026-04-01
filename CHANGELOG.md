CHANGELOG
=========

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------
- 今後のリリース予定: マイナー改善（ログ出力の強化、テストカバレッジ拡充）、および ETL の未完実装箇所の修正・完成化。

[0.1.0] - 2026-04-01
-------------------

Added
- パッケージ基盤
  - 初期バージョンを公開。パッケージ名: kabusys, __version__ = 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定・読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動読み込み（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env のパースを堅牢化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ処理を考慮。
    - インラインコメントの取り扱い（クォート有無での扱い差分）に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / システム環境などをプロパティ化。
    - 必須環境変数未設定時は ValueError を送出。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値のチェック）を実装。
    - Path や float 変換を行い、既定値を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ投げてセンチメント（-1.0〜1.0）を計算し ai_scores テーブルへ書き込み。
    - タイムウィンドウ: JST 前日 15:00 〜 当日 08:30（UTC に変換して DB 比較）。calc_news_window を提供。
    - バッチ処理: 最大 20 銘柄/回、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を利用し厳密な JSON 出力を期待するが、余計な前後テキスト混入にも耐えるパーサーを実装。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ実装。
    - レスポンスバリデーション: results 配列の存在、code/score の型チェック、既知コードのフィルタリング、スコアの有限性確認、±1.0 クリップ。
    - 部分成功時の DB 保護: スコア取得済みコードのみ DELETE → INSERT（executemany）で置換。
    - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api をパッチ可能に設計。
    - エラー耐性: API 失敗時は該当チャンクをスキップして処理継続（例外を上げずフェイルセーフ）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で regime_score を算出し market_regime テーブルへ冪等書き込み。
    - マクロセンチメントは raw_news からマクロキーワードで抽出したタイトルを OpenAI（gpt-4o-mini）に投げて JSON 出力を期待。
    - API 呼び出しに対するリトライ/フェイルセーフを実装（API 失敗時は macro_sentiment = 0.0 として継続）。
    - データ不足や過度な先読みを避けるため、prices_daily クエリは target_date 未満のデータのみを使用（ルックアヘッドバイアス対策）。
    - DB へは BEGIN / DELETE / INSERT / COMMIT の冪等書き込み。失敗時は ROLLBACK を試行。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR/株価比、20日平均売買代金、出来高比率を計算。NULL 値取り扱いに注意。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/NULL の場合は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度に計算する汎用実装（デフォルト [1,5,21]）。
    - calc_ic: スピアマン（ランク相関）による IC 計算。有効レコードが 3 未満なら None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties を安定化）。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を使った営業日判定・前後営業日の取得・期間内営業日取得（DB 値優先、未登録日は曜日ベースでフォールバック）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックあり。
  - pipeline / ETL:
    - ETLResult データクラスを公開（etl モジュール経由で再エクスポート）。
    - pipeline モジュールに ETL のユーティリティ（差分更新、品質チェック連携、保存カウンタ、error/quality issue 集約）を実装。
    - ETL の設計方針として、idempotent 保存、バックフィル、品質チェックは Fail-Fast とせず呼び出し元が対応する方式を採用。
  - DuckDB 互換性配慮:
    - executemany に空リストを渡せない（DuckDB 0.10）ケースへの回避処理を実装。
    - 日付変換ユーティリティ（_to_date）やテーブル存在チェックを提供。

- 設計原則・品質
  - ルックアヘッドバイアス防止: いずれの処理でも datetime.today() / date.today() に依存しない設計を徹底（target_date を明示的に受け取る）。
  - ID・冪等性: DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 等）して再実行可能性を確保。
  - フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時はフォールバック値または処理スキップでシステム全体の停止を回避。
  - テストのための差し替えフック（_call_openai_api を patch 可能など）を複数実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- OpenAI API キーや各種トークンは環境変数で管理（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
- 必須トークン未設定時は ValueError を送出して早期に検出。

Notes / Known issues
- 必須環境変数の未設定は明示的に例外となるため、運用時には .env（例 .env.example）または環境にて適切に設定してください。
- DuckDB のバージョン依存: executemany に空リストを渡せない等の仕様に合わせた回避を実装していますが、将来の DuckDB バージョン差分での挙動確認を推奨します。
- OpenAI SDK 依存: openai パッケージの例外型（APIError に status_code 属性があるか等）に対する互換処理を実装していますが、SDK の大幅な変更時は挙動確認が必要です。
- 部分的に未完成またはスニペット切れの可能性:
  - 提供コードの一部（pipeline._get_max_date の末尾など）で途中で切れている／不完全に見える箇所が確認されました。実運用前に該当箇所の実装・テストをお願いします。
- テスト支援:
  - OpenAI 呼び出しはモック化可能な設計（_call_openai_api のパッチ等）。ユニットテストでの外部 API 依存排除が容易です。

Migration / Upgrade notes
- 既存の運用環境から導入する場合:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を整備してください。
  - .env/.env.local の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化できます（CI / テストで便利）。
  - DuckDB のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が必要です。ETL/pipeline と併せてスキーマ準備を行ってください。

既知の将来対応予定
- ETL pipeline の未完実装箇所の完成・リファクタリング。
- モジュール間のドキュメント整備（API サンプル / デプロイ手順）。
- 監視・実行（execution, monitoring）モジュールの実装拡充・運用ガイドの追加。

-- End of CHANGELOG --