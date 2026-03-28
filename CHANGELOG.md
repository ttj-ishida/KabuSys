Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コード内容から推測して作成しています。実際のコミット履歴とは異なる可能性があります。

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28
初回リリース（推測）。日本株自動売買システムの基盤機能を実装。

### 追加
- パッケージ基礎
  - パッケージ初期化とバージョン管理を追加（src/kabusys/__init__.py）。

- 環境設定
  - .env / .env.local および OS 環境変数から設定を自動読み込みする設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を探索して検出（CWD非依存）。
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントに対応した .env パーサを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須変数未設定時には _require() が ValueError を発生させる Settings クラスを提供。
    - デフォルト設定（KABUSYS_ENV, LOG_LEVEL, DB パス等）と便利なプロパティ（is_live / is_paper / is_dev）を実装。

- AI（自然言語処理）
  - ニュースセンチメント解析モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols をまとめて銘柄ごとにテキスト集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを取得。
    - チャンク処理（最大20銘柄／チャンク）、記事トリム（文字数・記事数上限）、JSON Mode 応答パース、レスポンス検証機能を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装。
    - レスポンス検証で不正な値は無視し、スコアは ±1.0 にクリップ。
    - テストを想定した _call_openai_api の差し替え可能設計。
    - 公開 API: score_news(conn, target_date, api_key=None)。

  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF（1321）の200日移動平均乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出し（gpt-4o-mini）に対するリトライ／フォールバック処理（API失敗時は macro_sentiment=0.0）。
    - DuckDB の prices_daily/raw_news/market_regime を利用して冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計、prices_daily クエリは target_date 未満のデータのみ使用。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム（Data）
  - ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
    - 差分取得・backfill・品質チェックの考え方を実装。
    - ETLResult データクラスを公開（ETL の集計・エラー・品質問題の取り扱いを簡易化）。
  - マーケットカレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar に基づく営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - JPX カレンダーを J-Quants から差分取得し冪等保存する calendar_update_job を実装（バックフィル・健全性チェックあり）。

- リサーチ（Research）
  - ファクター計算と特徴量探索を追加（src/kabusys/research/*）。
    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum（1M/3M/6Mリターン・200日MA乖離）、Volatility（20日ATR・相対ATR・出来高指標）、Value（PER・ROE）を実装。
      - DuckDB での SQL 集約＋Python での整形。データ不足時は None を返す安全設計。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic：スピアマンランク相関）計算、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - z-score 正規化ユーティリティ（zscore_normalize）は data.stats から再エクスポートする形で提供（src/kabusys/research/__init__.py）。

- その他
  - OpenAI クライアント呼び出し点でテスト用にモック差し替え可能な設計を採用（各 ai モジュールの _call_openai_api）。
  - DuckDB 互換性を考慮した空リスト executemany 回避などの実装上の注意を反映。

### 変更
- セキュリティ／運用上の小さな配慮を反映
  - 環境変数の保護: .env 読み込み時に既存 OS 環境変数を protected として上書きを制御。
  - OpenAI API キー未設定時に明示的な ValueError を送出するように統一（score_news / score_regime）。

- 設計方針の明確化（コード内ドキュメント）
  - すべての分析・AI モジュールで「ルックアヘッドバイアス防止」の方針を採用（datetime.today() などを参照しない）。

### 修正（推測）
- ロバストネス向上
  - OpenAI 呼び出しに対して 429 / 接続断 / タイムアウト / 5xx を対象としたリトライと指数バックオフを実装し、全失敗時はフェイルセーフ（0.0やスキップ）で継続するようにした。
  - JSON レスポンスの不正や余計な前後テキスト混入に対する復元ロジックを追加（JSON の最外 {} を抽出してパースを試行）。

### 既知の制限・注意点
- 財務指標の一部（PBR・配当利回り）は現バージョンで未実装（calc_value に注記あり）。
- OpenAI モデルは gpt-4o-mini を前提にしている（将来のモデル名変更に注意）。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間で private 関数を共有しない設計。
- DuckDB のバージョン差異（executemany 空リスト扱い等）を考慮した実装が含まれるため、利用時の DuckDB バージョンに注意。
- calendar_update_job 等は外部 J-Quants クライアント（kabusys.data.jquants_client）に依存。API 呼び出しの例外はログ出力してゼロ返却する（外部エラーを上位で扱いやすくする）。

---

今後のリリースで追加が期待される項目（参考）
- PBR / 配当利回りなどバリューファクターの拡張
- ai モジュールのユニットテスト用のスタブ/インタフェース強化
- ETL パイプラインの CLI / スケジューラ統合
- 監視・通知（Slack 連携等）の実装（config で Slack トークン・チャネルは定義済み）

（以上）