CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

[0.1.0] - 2026-03-31
-------------------

追加 (Added)
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開用の __init__（src/kabusys/__init__.py）を追加し、主要サブパッケージをエクスポート:
    - data, strategy, execution, monitoring

- 環境設定 / ロード機構（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動検出してロードする自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
  - .env ファイルのパース強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートなしとクォートありで扱いを分離）
  - .env の上書きルール:
    - OS 環境変数を保護する protected セットを導入
    - .env（override=False）→ .env.local（override=True）の順で適用
  - Settings クラスを実装し、環境変数からアプリ設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（validation: development/paper_trading/live）
    - LOG_LEVEL（validation: DEBUG/INFO/...）
    - ヘルパー: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄毎のセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を追加。
    - 処理上の工夫:
      - スコア計算ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供
      - 1銘柄あたり最大記事数 / 最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
      - バッチ送信（最大 _BATCH_SIZE = 20 銘柄）
      - API 呼び出しのリトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）
      - レスポンスの厳格なバリデーション（JSON 抽出・results 構造・コード検証・数値検証）
      - DuckDB 互換性考慮（executemany の空リスト禁止を回避）
      - テスト容易性: _call_openai_api をモック差し替え可能
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う処理を追加。
    - 特徴:
      - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドを防止）
      - マクロ記事のキーワードベース抽出（_MACRO_KEYWORDS）
      - OpenAI 呼び出しのリトライ（RateLimit / 接続エラー / タイムアウト / 5xx を考慮）
      - API 失敗時は macro_sentiment=0.0 にフォールバックする堅牢性
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。エラー時は ROLLBACK を試行

- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から PER, ROE を計算（target_date 以前の最新財務データを使用）
    - 実装方針: DuckDB の SQL と Python の組合せで副作用なしに計算
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを取得
    - calc_ic: スピアマンのランク相関（IC）を計算
    - rank: 同順位は平均ランクで処理（浮動小数点丸め対策あり）
    - factor_summary: count/mean/std/min/max/median を計算
  - research パッケージの __init__ で主要関数を再エクスポート

- データプラットフォーム（src/kabusys/data）
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定ユーティリティを追加:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（土日除く）でフォールバックする一貫した挙動
    - calendar_update_job: J-Quants API からカレンダー差分取得 → 保存（バックフィル・健全性チェックを含む）
  - pipeline / ETL:
    - ETLResult データクラスを導入（取得件数、保存件数、品質問題、エラー一覧を保持）
    - ETL モジュール設計（差分更新、品質チェック、backfill、id_token の注入でテスト容易性）
    - data.etl で ETLResult を再エクスポート

- 共通技術的特徴
  - DuckDB を主要なデータ格納・クエリ基盤として一貫利用
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（関数は target_date を引数で受け取る）
  - OpenAI 呼び出しは JSON mode を使い厳密な JSON 出力を期待、テスト用に差し替え可能な抽象化を採用
  - API 呼び出しのフェイルセーフ設計（失敗時に処理継続、必要に応じて中立スコアでフォールバック）
  - 多くの箇所で冪等性（DELETE→INSERT、ON CONFLICT DO UPDATE など）を意識した実装

変更 (Changed)
- 初期リリースのため該当なし

修正 (Fixed)
- 初期リリースのため該当なし

既知の問題 (Known issues)
- src/kabusys/data/pipeline.py の末尾に実装が途中で途切れている箇所が存在します（現状: "return date.fro" のような不完全な文）。このままではパース/インポート時に SyntaxError などで実行不能になる恐れがあります。対象関数は _get_max_date の帰還処理の終了部分に相当すると推測され、正しい日付変換ロジック（例: date.fromisoformat や適切な型判定の戻し処理）で修正する必要があります。
- jquants_client 等の外部クライアントモジュール（fetch/save 系）は本リポジトリに含まれていない前提で実装されているため、実行環境にはこれらのクライアント実装またはモックが必要です。
- OpenAI API 利用部分は実行コストと API キーが必要です。API キーが未設定の場合は関数が ValueError を送出します（フェイルセーフだが事前準備が必要）。
- .env/.env.local の自動ロードはプロジェクトルート検出を行うため、配布形態や実行環境によっては期待通りに検出されない場合があります（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動制御してください）。

開発者向けメモ (For developers)
- テスト容易性のため、OpenAI 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）を unittest.mock.patch で差し替え可能に設計しています。
- DuckDB に対する executemany の挙動（空リスト不可）を回避するチェック（if params:）を行っています。DuckDB バージョン差異により注意してください。
- 環境変数の必須チェックは Settings._require を通じて行われます。CI/デプロイ時には必須環境変数の設定を忘れないでください。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴に基づく変更履歴が必要な場合は、git のログを基に更新してください。