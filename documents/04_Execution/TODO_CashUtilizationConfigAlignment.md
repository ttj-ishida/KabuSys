# TODO: 現金余力・投下上限ルールの設定ファイル統合

- ステータス: 未着手
- 目的: `どこまで使ってよいかの上限ルールは設定で管理する` を正しい設計とし、Execution 実装をその方針に合わせて修正する
- 対象: `RiskManager`, `run_execution.py`, 設定読み込み、関連ドキュメント

---

## 1. 背景

現状の実装では、現金余力の実額は broker API から取得している一方で、投下上限ルールは `run_execution.py` 内で `RiskConfig(...)` に直書きされている。

例:

- `max_position_pct=0.20`
- `max_utilization=0.80`
- `max_drawdown=0.20`

これは、設計上の「上限ルールは設定で管理する」という方針と一致していない。

また、全体上限の分母として使う `initial_portfolio_value` は、現在 `broker.get_available_cash()` をそのまま使っており、既存保有を含む総資産と一致しない場合がある。

---

## 2. 正とする設計

この TODO では、以下を正しい設計とする。

### 2.1 実余力

- 実際の現金余力は broker API から取得する
- 本番では kabuステーション API、paper では MockBrokerClient を使う

### 2.2 上限ルール

- `どこまで使ってよいか` の上限ルールは設定ファイルで管理する
- 実装は設定ファイルを読み込み、その値で `RiskManager` を構成する

### 2.3 総資産基準

- 全体投下上限や DD 判定の基準となる初期資産は、`現金余力` だけではなく、必要に応じて既存保有を含む総資産で評価する
- 少なくとも「何を基準値として使っているか」が明確に定義されている状態にする

---

## 3. 解消すべき現状差分

### 3.1 `RiskConfig` の直書き

現状:

- `run_execution.py` で `RiskConfig(...)` を直接生成している

あるべき姿:

- 設定ファイルまたは設定読み込み層から値を取得する

### 3.2 設定ファイル未接続

現状:

- `documents/01_Data/config_schema.md` には `risk_config.yaml` がある
- しかし `run_execution.py` の実行経路では、その値を読んでいない

あるべき姿:

- 実行時に `risk_config.yaml` 相当の設定が `RiskConfig` に反映される

### 3.3 総資産基準の曖昧さ

現状:

- `initial_portfolio_value` に `broker.get_available_cash()` を入れている

あるべき姿:

- `現金 + 保有評価額` を含む総資産基準にするか
- もしくは `現金基準` を意図的に採用するなら、その理由を設計書に明記する

---

## 4. 実装変更 TODO

## 4.1 設定スキーマを正式な実行入力として接続する

- `risk_config.yaml` の値を Execution 起動時に読み込む仕組みを作る
- 少なくとも以下を設定化対象にする
  - `max_position_pct`
  - `max_utilization`
  - `max_drawdown`
  - `rate_limit_per_sec`
  - `circuit_breaker_errors`
  - `circuit_breaker_window_sec`

注意:

- 現在の `config_schema.md` にあるキー名と、`RiskConfig` のフィールド名の差分を整理する
- `max_position_size` と `max_position_pct` の名称統一が必要

## 4.2 `run_execution.py` の直書き値を撤去する

- `RiskConfig(...)` の固定値指定をやめる
- 設定読み込み結果から `RiskConfig` を構築する
- デフォルト値は設定層に寄せ、実行コード内に散在させない

## 4.3 `RiskConfig` と設定ファイルキーの対応表を定義する

例:

- `risk.max_position_size` -> `RiskConfig.max_position_pct`
- `risk.max_drawdown` -> `RiskConfig.max_drawdown`
- `risk.max_portfolio_exposure` または別キー -> `RiskConfig.max_utilization`

TODO:

- 命名差分を吸収する変換層を作るか
- `RiskConfig` 側の名前を設定スキーマに寄せるかを決める

## 4.4 初期総資産の取得方法を見直す

現状の `broker.get_available_cash()` だけでは、既存保有があるケースで総資産にならない。

TODO:

- 起動時に `broker.get_positions()` を取得する
- `current_price` があれば評価額を計算する
- `current_price` がなければ `avg_price` で保守的に代替する
- `initial_portfolio_value = available_cash + market_value` を候補として整理する

## 4.5 設定未読込時のフォールバック方針を決める

TODO:

- 設定欠落時に起動失敗させるか
- 保守的なデフォルトで起動させるか
- `live` 環境では fail-fast、`development/paper_trading` ではデフォルト許容とするか

## 4.6 paper_trading と live で同じ設定パスを使う

- `paper_trading` でも `RiskConfig` は同じ設定読み込み経路を使う
- 差分は broker 実装と DB パスだけに寄せる
- ルール差分が必要なら、環境別設定ファイルで吸収する

---

## 5. テスト観点

## 5.1 設定反映テスト

- 設定ファイルの `max_utilization` を変えると `RiskManager` の挙動が変わる
- 設定ファイルの `max_position_pct` を変えると銘柄上限判定が変わる
- 設定ファイルの `max_drawdown` を変えると kill switch 判定が変わる

## 5.2 総資産基準テスト

- 現金のみの口座
- 保有ありの口座
- `current_price` なしの保有

上記で `initial_portfolio_value` が意図通りになることを確認する

## 5.3 環境別テスト

- `development`
- `paper_trading`
- `live`

で同じ設定読み込み経路が使われることを確認する

---

## 6. 変更対象候補ファイル

### 実装

- `src/kabusys/run_execution.py`
- `src/kabusys/execution/risk_manager.py`
- `src/kabusys/config.py`
- 必要なら新規設定ローダーモジュール

### 設計書

- `documents/04_Execution/ExecutionSystem.md`
- `documents/06_RiskManagement/RiskManagement.md`
- `documents/01_Data/config_schema.md`

---

## 7. 設計書への反映ポイント

### `ExecutionSystem.md`

- 実余力は broker API 取得であることを明記する
- 上限ルールは設定ファイルから読み込むことを明記する

### `RiskManagement.md`

- `max_position_pct`
- `max_utilization`
- `max_drawdown`

が設定可能パラメータであることを明記する

### `config_schema.md`

- 実際に使うキー名に合わせてスキーマを更新する
- `max_portfolio_exposure` と `max_utilization` の関係を整理する

---

## 8. まず決めるべきこと

### 優先度高

1. 設定ファイルの正式なキー名
2. `RiskConfig` とのマッピング方法
3. `initial_portfolio_value` を現金基準にするか総資産基準にするか

### 優先度中

1. 環境別の設定切り替え方法
2. 設定欠落時の挙動

### 優先度低

1. 実行中に設定変更を再読込するか
2. UI から変更可能にするか

---

## 9. 完了条件

以下を満たせば、この TODO は完了とする。

1. Execution の上限ルールがコード直書きではなく設定から読み込まれる
2. 実余力は引き続き broker API から取得される
3. 総資産基準の扱いが実装と設計で一致する
4. `production` / `paper_trading` / `development` で同じ設定方針が使われる
5. 関連設計書の説明と実装が一致する
