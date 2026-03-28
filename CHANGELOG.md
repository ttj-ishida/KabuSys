CHANGELOG
=========
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

[0.1.0] - 2026-03-28
--------------------

Added
- 初期リリース (0.1.0) — 日本株自動売買支援ライブラリ「KabuSys」を追加。
- パッケージ公開情報
  - パッケージルート: src/kabusys/__init__.py による基本公開 (version=0.1.0)。
  - サブパッケージを __all__ で公開: data, strategy, execution, monitoring（将来の拡張を想定）。
- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数の自動読込みを実装（優先順: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等で使用）。
  - 高度な .env パーサ:
    - export KEY=val 形式対応、クォート文字列内のバックスラッシュエスケープ対応、コメント除去ロジック。
    - 読み込み時に既存 OS 環境変数を保護する protected パラメータによる上書き制御。
  - Settings クラスを提供し、必須環境変数取得時に未設定なら ValueError を発生:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須変数をプロパティで提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック。
    - DB パスのデフォルト（duckdb/sqlite）と is_live/is_paper/is_dev ヘルパーを提供。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄毎のニュースを OpenAI（gpt-4o-mini）で一括センチメント評価し ai_scores テーブルへ書き込み。
  - 特徴:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - 1チャンク最大 20 銘柄に対するバッチ送信、1銘柄あたり最大 10 記事・最大 3000 文字でトリム。
    - JSON Mode を利用した厳密なレスポンス期待と、前後余計テキストの補正ロジック（{} の抽出）。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスバリデーション: results 配列の存在、各要素の code/score、未知コードの無視、スコアの ±1.0 クリップ。
    - 部分失敗を考慮した DB 書き込み: 取得できたコードのみ DELETE → INSERT（トランザクション & ROLLBACK 保護）。
    - API 呼び出し関数はテスト容易性のため _call_openai_api で抽象化して置換可能。
- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）を行い market_regime に冪等書き込み。
  - 特徴:
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。データ不足時は中立(1.0)フォールバック。
    - マクロニュース抽出（指定キーワード群によるタイトルフィルタリング、最大20件取得）。
    - OpenAI 呼び出し（gpt-4o-mini）で JSON 出力を期待し macro_sentiment を抽出、API エラー時は 0.0 にフォールバック。
    - 合成スコア clip 及び閾値判定でラベル付与、冪等な DB 書き込み(DELETE/INSERT) とトランザクション保護。
    - OpenAI クライアント呼び出しは _call_openai_api で抽象化（テスト差替え可能）。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials からの EPS/ROE 結合による PER/ROE（EPS 0/欠損時は None）。PBR/配当利回りは未実装として明記。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API や発注処理には影響しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算（複数ホライズンを一度のクエリで処理）。
    - calc_ic: Spearman ランク相関（情報係数）を計算。充分な有効レコードがない場合 None を返す。
    - rank: 同順位は平均ランクへ変換（丸め処理による ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - research パッケージで主要ユーティリティを再エクスポート（zscore_normalize 等）。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベース（平日）でフォールバック。DB がまばらでも一貫した振る舞いを保証。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline (ETL):
    - ETLResult データクラスを定義し、ETL 実行結果・品質問題・エラー概要を構造化して返す。
    - 差分更新、バックフィル、品質チェック（quality モジュール）との連携を想定した設計。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、トレードデイ調整ロジック等。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client (呼び出し先は別モジュール): fetch/save を通じて DB へ冪等保存する設計を想定。
- 一貫した設計方針／信頼性改善
  - ルックアヘッドバイアス回避のため、score_news / score_regime /ファクター計算等は date 引数を受け取り datetime.today()/date.today() を直接参照しない実装。
  - OpenAI や外部 API 呼び出しに対するフォールバック（macro_sentiment=0.0 など）とリトライ（指数バックオフ）を広く導入。
  - DB 操作はトランザクションで保護し、失敗時は ROLLBACK を試みてログ出力。
  - テスト容易性のため、OpenAI 呼び出しをラップして patch しやすくしている（ユニットテスト向け）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 初版のため特記事項なし。環境変数取り扱いは protected set による OS 環境保護を導入。

Notes / Known limitations
- raw_financials による PBR や配当利回りは現バージョンでは未実装と明記。
- jquants_client 実装（外部 API ラッパー）はライブラリ内で参照される前提だが、ここに含まれるコードスニペットでは実体は省略されている（別モジュール／依存として実装が必要）。
- OpenAI モデルは gpt-4o-mini を想定。API 仕様や SDK の変更により微調整が必要になる可能性あり。
- DuckDB のバインド挙動（executemany に空リスト不可など）を考慮した処理を導入している。

取り扱い方針
- 重大なバグ修正や API 互換変更がある場合はセマンティックバージョニングに従いメジャー/マイナー/パッチで管理します。
- 以降のリリースではユニットテストの充実、ドキュメント（使用例・マイグレーション手順）の追加を優先予定。