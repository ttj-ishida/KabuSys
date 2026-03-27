# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン情報はパッケージの src/kabusys/__init__.py にある __version__ を参照しています。

文書構成:
- Unreleased: 今後の変更（空）
- 各リリース: 日付付きで主要な追加・変更点を列挙

## [Unreleased]

---

## [0.1.0] - 2026-03-27

初回リリース（ベース実装）。日本株自動売買システム「KabuSys」のコア機能群を提供します。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール（__all__）: data, strategy, execution, monitoring（外部公開インターフェースを意図的に分離）

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数の自動読み込み機能を実装
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後も動作）
  - .env パーサの実装（export 形式 / シングル・ダブルクォート / エスケープ / 行内コメントの扱い等を考慮）
  - 環境変数必須チェック用のヘルパー _require と Settings クラスを提供
    - 提供プロパティ例: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
    - env と log_level は許容値チェックを実施（不正な値は ValueError）

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄毎のセンチメントを評価
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄当たり記事最大 10 件・3000 文字にトリム
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx を Exponential backoff でリトライ
    - レスポンス検証: JSON パース復元（前後余計テキストの切り出し）、results 配列と code/score の検証、スコアは ±1.0 でクリップ
    - DB 書き込み: 部分失敗時に既存データを守るため、対象コードに対して DELETE → INSERT の冪等操作を実施
    - テスト容易性: OpenAI 呼び出し部分をモック可能（_call_openai_api を patch 可能）
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（NIKKEI 連動型）の 200 日移動平均乖離（重み70%）とニュース由来マクロセンチメント（重み30%）を組み合わせて日次でレジーム（'bull' / 'neutral' / 'bear'）を判定
    - マクロニュース抽出はニュース NLP のウィンドウと連携（calc_news_window を利用）
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用し、API の障害時は macro_sentiment=0.0 として継続（フェイルセーフ）
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止
    - DB 書き込みは冪等 (BEGIN / DELETE WHERE date=... / INSERT / COMMIT)
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1 を返す（成功時）

- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルの読み書き・夜間更新ジョブ calendar_update_job を提供
    - 営業日判定 / 前後営業日取得 / 期間内営業日取得 / SQ日判定のユーティリティ群を実装
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバックする一貫した挙動
    - 最大探索範囲やバックフィル、健全性チェック（極端な将来日付のスキップ）を実装
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL の実行結果集約）
    - 差分取得、保存（jquants_client の save_* を想定して冪等保存）、品質チェックを行う設計
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得、トレーディング日補正等
    - jquants_client（外部クライアント）との連携を想定して実装（fetch/save 呼び出し箇所）
  - jquants_client と quality モジュールを呼び出す設計（外部 API との分離）

- リサーチ / ファクター群 (src/kabusys/research)
  - factor_research モジュール
    - モメンタム (1M/3M/6M)、200日 MA 乖離、ATR（20日）、平均売買代金、出来高比率、PER/ROE（raw_financials）などを計算
    - DuckDB 上で SQL を用いて計算（外部 API 呼び出し無し）
    - 関数: calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date)
  - feature_exploration モジュール
    - 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ランク付けユーティリティ (rank)、統計サマリー (factor_summary)
    - pandas 等の外部依存を使わず標準ライブラリ + DuckDB で実装
  - data.stats からの zscore_normalize を再エクスポート（research パッケージ初期化）

### 設計上の注意・フェイルセーフ
- 全般
  - ルックアヘッドバイアス防止のため、score_news/score_regime 等は datetime.today()/date.today() を内部で参照しない（外部から target_date を渡す）
  - DuckDB を主要なデータ格納先として扱い、SQL（ウィンドウ関数等）で集計・計算
  - DB 書き込みは可能な限り冪等操作を採用（DELETE → INSERT / ON CONFLICT を想定）
  - OpenAI 呼び出しは JSON モードを利用しレスポンスの堅牢な検証を行う
  - API 障害時は「スキップ + ログ出力」またはデフォルト値（例: macro_sentiment=0.0, ma200_ratio=1.0）で継続する設計
  - テスト容易性を考慮し、OpenAI への実際の呼び出しを差し替え可能（内部 _call_openai_api の patch）

### 既知の制約 (Known issues / Limitations)
- strategy, execution, monitoring の実装詳細は本リリースでの公開インターフェースに含まれるが、ここに含まれるファイル群からは未確認の部分があり得る（パッケージ初期化で公開）。
- 一部 DuckDB の API バインドの扱い（executemany に空リストを渡せない等）を考慮した実装上の条件分岐あり。
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY のいずれかで供給する必要がある。未設定時は ValueError を送出。

---

（注）本 CHANGELOG はソースコードの内容から推測して作成したものであり、実際のリリースノートやドキュメントと異なる場合があります。必要であればリリース日や細部説明の修正を行います。