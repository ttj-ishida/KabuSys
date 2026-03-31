# CHANGELOG

すべての notable な変更点はこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。  
公開バージョンはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買システム「KabuSys」の基本機能を実装しました。主にデータ基盤、リサーチ（ファクター計算）、AI ベースのニュース解析／レジーム判定、設定管理および ETL/カレンダー管理のコアモジュールを含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys。トップレベルで data, strategy, execution, monitoring を公開する設計（__all__）。
  - バージョン定義: __version__ = "0.1.0"。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルートの .git または pyproject.toml を検出して .env / .env.local を順に読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー: export KEY=val 形式、クォート（シングル／ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - .env.local は .env を上書きする挙動（ただし OS の既存環境変数は保護され上書きされない）。
  - 必須環境変数取得用の _require ヘルパーと、J-Quants / kabuステーション / Slack / DB / 監視設定などのプロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
  - KABUSYS_ENV の許容値（development, paper_trading, live）や LOG_LEVEL のバリデーション。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄毎のセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して DB クエリで使用）。
    - バッチサイズ、記事数・文字数のトリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ。
    - レスポンスの厳密な JSON 検証とスコアの ±1.0 クリップ。
    - 取得成功分のみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT の一部置換）。
    - テスト容易性のため _call_openai_api をモック可能。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して、日次で market_regime に書き込み（'bull' / 'neutral' / 'bear'）。
    - ma200_ratio 計算は target_date 未満のデータのみ使用してルックアヘッドを防止。
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI による JSON 出力をパースして macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK を試行。

- リサーチ・ファクター計算 (kabusys.research)
  - factor_research
    - モメンタム: mom_1m / mom_3m / mom_6m と 200 日 MA 乖離（ma200_dev）の計算を実装（prices_daily をクエリ）。
    - ボラティリティ/流動性: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金・出来高比率等の算出。
    - バリュー: raw_financials から EPS/ROE を参照して PER/ROE を算出（target_date 以前の最新財務データを使用）。
    - データ不足時は None を返す安全設計。
  - feature_exploration
    - 将来リターン計算 (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21] 営業日）に対する fwd_xd を生成。horizons の検証あり。
    - IC 計算 (calc_ic): スピアマンのランク相関（ランクは平均ランクを採用、ties を考慮）。
    - ランク変換 (rank): 丸め処理で ties の検出漏れを抑止。
    - 統計サマリ (factor_summary): count/mean/std/min/max/median を返す。外部ライブラリに依存せず標準ライブラリで実装。

- データ基盤 (kabusys.data)
  - calendar_management
    - market_calendar に基づく営業日判定とユーティリティ関数を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベース（平日のみを営業日）でフォールバック。DB 登録値が優先され、未登録日は一貫したフォールバックロジックを採用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新。バックフィルや健全性チェックを実装（直近の再フェッチ・将来日付の異常検出など）。
  - pipeline / etl
    - ETLResult データクラスを公開（データ取得・保存件数、品質問題、エラーリストなどを保持）。
    - pipeline モジュールの骨子（差分取得、保存、品質チェックのフロー設計）。デフォルトの backfill 動作やカレンダ先読み等を定義。
    - DuckDB を主要な永続化層として利用する設計。

### 変更 (Changed)
- なし（初回リリース）。ただしモジュール設計上、以下の仕様を明確化：
  - すべての日時処理ではルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない方針（関数引数で基準日を与える）。
  - DuckDB を前提として SQL を記述。互換性のため executemany の空リスト送信に注意した処理を行う。

### 修正 (Fixed)
- なし（初回リリース）。

### 注意点 / 既知の制限 (Notes / Known issues)
- OpenAI クライアントは gpt-4o-mini と JSON Mode を想定している。API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用する必要がある。未設定時は ValueError を送出する。
- news_nlp および regime_detector は API 通信失敗時にフェイルセーフとしてスコア 0.0 を使う（例外を上位へ伝播させず処理を継続する部分あり）。部分的なデータ欠損時でも既存 DB データを保護する書き込み戦略を採用。
- ETL / calendar_update_job / pipeline の J-Quants 連携部分は jquants_client に依存（モック可能）。実運用前に API レート・認証・エラー処理の再確認を推奨。
- strategy / execution / monitoring パッケージはトップレベルで公開される想定だが、本リリースでの中身はこの changelog の対象外（将来的に追加・拡張予定）。

---

今後のリリースでは以下を想定しています（未実装／予定）:
- strategy / execution の受発注ロジック（kabuステーション連携・注文管理）の実装とテスト。
- モニタリング・アラート（Slack 通知）の統合。
- 性能改善（大規模データ用の最適化）、ユニットテスト／統合テストの充実化。

もし特定モジュールについてさらに詳しい変更履歴や注釈が必要であれば教えてください。