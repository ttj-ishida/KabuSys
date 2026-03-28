# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に準拠しています。  

※日付はリリース日を示します。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-28
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを導入。公開 API として data, research, ai, config などのサブパッケージを提供。
  - バージョン情報: 0.1.0

- 環境設定 / ロード (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env パーサを実装し、以下をサポート:
    - 空行・コメント行（#）無視、行頭の `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しでの行内コメント扱い（直前がスペース/タブの場合のみ）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスを実装し、必須設定の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）と既定値の管理（例: KABUS_API_BASE_URL、DBパス、LOG_LEVEL, KABUSYS_ENV）。環境値の検証（env, log_level の許容値）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols データを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存する機能を追加。
  - 処理の特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算（calc_news_window）
    - 1銘柄あたりの最大記事数・文字数制限（トークン肥大化対策）
    - バッチ処理（最大 20 銘柄 / API コール）
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト形式、code/score の検証）
    - スコアを ±1.0 にクリップ
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ、失敗時は該当チャンクをスキップして継続（フェイルセーフ）
    - DuckDB の executemany の制約を考慮した安全な DELETE→INSERT の置換ロジック（部分失敗時に既存データを保護）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を追加。
  - 処理の特徴:
    - MA200 乖離計算（ルックアヘッド防止: target_date 未満のデータのみ使用）
    - マクロニュース抽出（キーワードフィルタ）→ OpenAI によるセンチメント評価
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）
    - OpenAI 呼び出しに対するリトライ（429・接続・タイムアウト・5xx を考慮）
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT による冪等実装、失敗時は ROLLBACK（再試行や上位での例外処理に対応）

- リサーチ / ファクター（kabusys.research）
  - ファクター計算モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比率
    - calc_value: PER（EPS が有効な場合）、ROE（raw_financials から最新レコードを取得）
  - 特徴量探索モジュールを追加:
    - calc_forward_returns: 将来リターン（任意 horizon の LEAD を利用）
    - calc_ic: スピアマンランク相関（ランク付け・同順位は平均ランク）
    - factor_summary: 各ファクターの基本統計（count/mean/std/min/max/median）
    - rank: 値をランクに変換（丸めで ties の検出安定化）
  - 実装方針:
    - DuckDB 上で SQL と標準ライブラリのみで計算（外部依存最小化）
    - ルックアヘッドバイアス対策（date を明示的に受け取り、today() を参照しない）

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management):
    - JPX カレンダー（market_calendar）を扱うユーティリティを追加（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録があれば DB 値優先、未登録日はフォールバックで一貫した挙動を提供。
    - 夜間バッチ更新ジョブ（calendar_update_job）: J-Quants から差分取得→save_market_calendar 呼び出し→保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline, etl):
    - ETLResult データクラスを公開し、ETL 処理の取得数・保存数・品質問題・エラーを集約できるようにした。
    - 差分取得、バックフィル、品質チェックの設計方針を反映。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- OpenAI 呼び出しや DB 書込みでの失敗に対する堅牢なハンドリングを実装:
  - API の 5xx/429/タイムアウト/接続断等に対してリトライとバックオフを実装し、最終的に安全なフォールバック（スコア 0.0 またはチャンクスキップ）を行うことで全体処理の停止を防止。
  - DuckDB の executemany の空リスト制約やリストバインドの互換性問題を回避する実装（空時は実行しない、DELETE を個別に executemany で実行する等）。
  - DB トランザクションに対して ROLLBACK の失敗を警告ログに出すなど、例外発生時の後処理を堅牢化。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する（呼び出し側でキー注入が必要）。
- ニュース・レジーム判定いずれも外部 API に依存しているため、API 利用料やレート制限には注意が必要。
- DuckDB の型戻り値（date など）に対しては互換性のため型変換処理を多用している（環境差異に起因する挙動に注意）。
- 本バージョンでは一部指標（PBR・配当利回りなど）は未実装。

### セキュリティ (Security)
- 本リリースにセキュリティ修正は含まれていません。

---

今後のリリースでは、テストカバレッジの強化、API 呼び出しの抽象化（モック容易化）、追加ファクターやパフォーマンス改善、GUI/ダッシュボードや発注実装の段階的追加を予定しています。