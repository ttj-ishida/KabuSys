# Changelog

すべての重要な変更点を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: セマンティックバージョニングに準拠しています。

## [Unreleased]

(今後の変更履歴をここに記載します)

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買・リサーチ・データ基盤向けの基本モジュール群を実装しました。主要な機能群と設計上の重要点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージの初期実装。パッケージバージョンは `0.1.0`。
  - パッケージの公開インターフェースに data / research / ai / その他サブパッケージを含める。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 複数の .env パーシングルールに対応（export プレフィックス、シングル/ダブルクォート、インラインコメント等）。
  - 環境変数ラッパー Settings クラスを提供（J-Quants / kabu / LINE / DB / 監視 / システム設定など）。
  - 必須変数未設定時は明示的に ValueError を送出する `_require` を実装。
  - 設定値のバリデーション（KABUSYS_ENV/LOG_LEVEL の許容値チェック）とヘルパープロパティ（is_live 等）。

- データ処理・ETL（src/kabusys/data/*）
  - ETL 結果を表す ETLResult dataclass を公開（pipeline.ETLResult を再エクスポート）。
  - pipeline モジュール: 差分取得、バックフィル、品質チェックを想定した ETL の基盤実装（DuckDB を使用）。
  - calendar_management: 市場カレンダー管理（market_calendar テーブル参照）、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）、夜間カレンダー更新ジョブ（calendar_update_job）。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した振る舞い。
    - 最大探索範囲やバックフィル、健全性チェックを実装して安全性を確保。
  - ETL/カレンダー関連で J-Quants クライアント呼び出し箇所を想定（jquants_client 経由）。

- AI / ニュースNLP（src/kabusys/ai/*）
  - news_nlp.score_news: raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC で前日 06:00 〜 23:30）を採用。
    - バッチ処理（最大20銘柄/リクエスト）、記事トリミング（最大記事数・最大文字数）でトークン肥大化を抑制。
    - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。未指定時は ValueError。
    - テスト容易性を考慮し、API 呼び出し箇所を差し替え可能（モジュール内の private 関数を patch してテスト）。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド回避）。
    - マクロニュースは news_nlp の calc_news_window を利用してウィンドウ抽出、OpenAI でマクロセンチメントを評価。
    - API エラーやパース失敗時は macro_sentiment=0.0 としてフォールバックするフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）。未指定時は ValueError。

- Research（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（PBR 等は未実装）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグを考慮。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸め対策付き）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
  - research パッケージは data.stats の zscore_normalize を再エクスポートしている。

### Changed
- （初期リリースのため既存機能の変更履歴はなし）

### Fixed
- （初期リリースのため修正履歴はなし）

### Security
- OpenAI API キーや重要値は Settings 経由で厳格に扱う設計。自動ロードは環境変数で無効化可能（テストや CI 向け）。

### Notes / 設計上の重要事項
- ルックアヘッドバイアス対策:
  - target_date を引数にとり、datetime.today()/date.today() を内部ロジックで参照しない設計を徹底（score_news / score_regime / 各種ファクター）。
- DB 書き込みの冪等性:
  - market_regime / ai_scores / その他保存処理は既存レコードを削除してから挿入する等、冪等性に配慮。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は処理を継続する（スコアを 0 にする、あるいは該当コードをスキップ）方針。
- テスト容易性:
  - OpenAI 呼び出しをラップしており、ユニットテストでは差し替え可能（unittest.mock.patch 指定箇所をコメントに明記）。
- 外部依存:
  - DuckDB を主要なローカルデータストアとして想定。
  - OpenAI SDK（chat completions）、J-Quants クライアント（jquants_client）想定のインターフェースを利用。

### Removed
- （初期リリースのため削除履歴はなし）

---

今後の予定（メモ）
- ai.score_news / regime_detector の応答フォーマット・プロンプト改良、バッチ最適化。
- ETL の実行スケジューラ・監視/アラート（LINE 通知等）統合。
- research の追加ファクター（PBR/配当利回り等）実装。
- テストカバレッジ拡充と CI パイプライン整備。

---
この CHANGELOG はコードの内容から推測して作成しています。記載内容に誤りや不足がありましたら、対象箇所（モジュール名・関数名）を指定の上、修正点をご指示ください。