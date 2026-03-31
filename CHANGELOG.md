# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

なお、本CHANGELOGはソースコードのコメント・ドキュメントから実装内容を推測して作成しています。

## [Unreleased]

### 追加予定 / 検討中
- なし（初期リリースにて主要機能を実装）

---

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点と設計上の重要事項は以下の通りです。

### 追加
- パッケージ基礎
  - kabusys パッケージ初期構成（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - ロード優先順位: OS 環境変数 > .env.local > .env
    - パッケージ配布後も動作するよう、__file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索して .env を解決。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーの実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント判定など）。
  - 環境変数の保護機能（既存 OS 環境変数を protected set として扱う）。
  - Settings クラスでアプリ設定を型付きプロパティとして提供（API トークン、DB パス、監視閾値、環境・ログレベル検証など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効値セットを定義）。
    - 必須値未設定時は ValueError を送出する _require を提供。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを生成し、OpenAI (gpt-4o-mini) の JSON mode へバッチ送信して銘柄別スコアを取得。
    - 一銘柄あたりのトークン肥大化対策（最大記事数・最大文字数をトリム）。
    - チャンクサイズ (_BATCH_SIZE=20)、リトライ（指数バックオフ）、429/ネットワーク断/タイムアウト/5xx を再試行対象とする堅牢性設計。
    - レスポンスバリデーションとスコアの ±1.0 クリップ。
    - 書き込みは「取得済みコードの置換」方針（DELETE → INSERT）で冪等性・部分失敗時の既存データ保護を実現。
    - テスト容易性: OpenAI 呼び出しは _call_openai_api を経由しており、テストで差し替え可能。
    - タイムウィンドウ計算 (calc_news_window): JST ベースのニュース集計ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime に変換して DB クエリに利用。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードリストに基づくフィルタを使用（最大 20 件）。
    - OpenAI 呼び出しは専用の _call_openai_api を使用（news_nlp とは分離）。
    - API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を内部で参照しない設計、prices_daily のクエリで target_date 未満のみ使用。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB データが存在しない/未登録日の場合は曜日ベース（土日）でフォールバックする一貫した挙動。
    - 夜間バッチ更新ジョブ (calendar_update_job) を実装。J-Quants クライアント経由で差分取得・idempotent 保存（fetch/save 呼び出しを外部 jq クライアントへ委譲）。
    - 再取得（バックフィル）や健全性チェック（極端に未来の日付を検出してスキップ）を実装。
  - ETL (pipeline, etl)
    - ETLResult データクラスを公開。ETL の取得数、保存数、品質問題、エラー概要を集約して返却可能。
    - ETL 設計方針の実装（差分更新、バックフィル日数、品質チェックの継続方針、テスト容易性のため id_token 注入等）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - duckdb 互換性考慮（executemany に空リストを渡さないなど）を明示。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - ボラティリティ / 流動性 (calc_volatility): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - バリュー (calc_value): raw_financials と prices_daily を組み合わせて PER/ROE を計算（EPS が 0/欠損時は None）。
    - 設計上、prices_daily/raw_financials のみ参照し、本番発注 API 等へアクセスしない。
  - feature_exploration モジュール:
    - 将来リターン (calc_forward_returns): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証を実施。
    - IC 計算 (calc_ic): factor と forward returns を code で結合してスピアマンのランク相関を計算（有効レコードが 3 件未満なら None）。
    - ランク変換 (rank): 同順位は平均ランクで処理。丸め処理で ties の誤判定を抑制。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算（None を除外、標準ライブラリのみで実装）。

### 変更（設計上の重要仕様）
- OpenAI 連携
  - 使用モデル: gpt-4o-mini（JSON mode を利用）。
  - API レスポンスの耐性強化: JSON parse 失敗時に文字列から最外殻の JSON を抽出して復元する処理を実装。
  - リトライロジック・バックオフを共通方針で採用。5xx は再試行対象、非 5xx エラーは速やかにフォールバック。
  - テスト容易性のため、内部の API 呼び出し関数を patch 可能に実装。

- データベース操作
  - 市場レジーム・AI スコア等の DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT、例外時は ROLLBACK）し、ROLLBACK の失敗ログ出力を行う安全策を実装。
  - DuckDB のバージョン差異に配慮した実装（executemany の空リスト禁止など）。

- バイアス防止
  - すべてのデータ処理関数は内部で現在日時を参照しない設計（target_date を明示的に受け取り、ルックアヘッドバイアスを防止）。

### 修正 / 不具合対応
- 初期リリースのため特定の「修正」はなし。ただし実装上以下の堅牢化が行われている点を記載:
  - API キー未設定時の明示的な例外（ValueError）を導入し、誤動作を早期検出可能に。
  - OpenAI レスポンスパース失敗時や API 障害時にスコアを 0.0 にフォールバックするなど、外部依存に対するフェイルセーフを多用。
  - market_calendar の NULL 値や未登録日に対して警告ログを出しつつ曜日フォールバックを採用。

### セキュリティ
- 現時点で公開すべきセキュリティ修正は無し。設定管理には環境変数ベースの機微情報（API トークン等）を想定しており、.env 自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

発行: kabusys 0.1.0 初期リリース（ドキュメント／実装コメントに基づく要約）